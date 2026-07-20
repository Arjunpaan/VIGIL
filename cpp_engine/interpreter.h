#ifndef INTERPRETER_H
#define INTERPRETER_H

#include "ast_nodes.h"
#include "moving_average.h"
#include "lookback_value.h"
#include <map>
#include <optional>
#include <stdexcept>
#include <vector>
#include <string>

class Interpreter {
private:
    std::vector<ASTNodePtr> program;
    std::map<std::string, double> env;
    std::map<std::string, double> prev_env;
    std::map<std::string, double> current_bar;
    std::map<std::string, MovingAverage> stateful_objects;
    std::map<std::string, LookbackValue> lookback_objects;

    std::optional<double> eval_expr(const ASTNodePtr& node, const std::map<std::string, double>& bar, const std::string& var_name) {
        if (auto n = std::dynamic_pointer_cast<NumberLiteral>(node)) {
            return n->value;
        }

        if (auto n = std::dynamic_pointer_cast<Identifier>(node)) {
            auto bar_it = bar.find(n->name);
            if (bar_it != bar.end()) {
                return bar_it->second;
            }
            auto env_it = env.find(n->name);
            if (env_it != env.end()) {
                return env_it->second;
            }
            return std::nullopt;
        }

        if (auto n = std::dynamic_pointer_cast<FunctionCall>(node)) {
            if (n->name == "moving_average") {
                std::optional<double> source = eval_expr(n->args[0], bar, var_name);
                auto window_node = std::dynamic_pointer_cast<NumberLiteral>(n->args[1]);
                int window = static_cast<int>(window_node->value);

                if (stateful_objects.find(var_name) == stateful_objects.end()) {
                    stateful_objects.emplace(var_name, MovingAverage(window));
                }

                if (!source.has_value()) return std::nullopt;
                return stateful_objects.at(var_name).update(source.value());
            }

            if (n->name == "price_n_days_ago") {
                std::optional<double> source = eval_expr(n->args[0], bar, var_name);
                auto lookback_node = std::dynamic_pointer_cast<NumberLiteral>(n->args[1]);
                int lookback = static_cast<int>(lookback_node->value);

                if (lookback_objects.find(var_name) == lookback_objects.end()) {
                    lookback_objects.emplace(var_name, LookbackValue(lookback));
                }

                if (!source.has_value()) return std::nullopt;
                return lookback_objects.at(var_name).update(source.value());
            }

            if (n->name == "percent_change") {
                std::optional<double> a = eval_expr(n->args[0], bar, var_name);
                std::optional<double> b = eval_expr(n->args[1], bar, var_name);

                if (!a.has_value() || !b.has_value()) return std::nullopt;
                return (a.value() - b.value()) / b.value() * 100.0;
            }

            throw std::runtime_error("Unknown function: " + n->name);
        }

        throw std::runtime_error("Cannot evaluate node");
    }

    bool eval_condition_node(const ASTNodePtr& node) {
        if (auto logic = std::dynamic_pointer_cast<LogicalOp>(node)) {
            bool left_result = eval_condition_node(logic->left);
            bool right_result = eval_condition_node(logic->right);
            if (logic->op == "and") return left_result && right_result;
            if (logic->op == "or") return left_result || right_result;
            throw std::runtime_error("Unknown logical operator: " + logic->op);
        }

        auto bin = std::dynamic_pointer_cast<BinaryOp>(node);
        if (!bin) throw std::runtime_error("Expected BinaryOp or LogicalOp");

        auto left_id = std::dynamic_pointer_cast<Identifier>(bin->left);
        auto right_id = std::dynamic_pointer_cast<Identifier>(bin->right);

        auto lookup = [&](const std::shared_ptr<Identifier>& id) -> std::optional<double> {
            auto bar_it = current_bar.find(id->name);
            if (bar_it != current_bar.end()) return bar_it->second;
            auto env_it = env.find(id->name);
            if (env_it != env.end()) return env_it->second;
            return std::nullopt;
        };

        std::optional<double> left = left_id ? lookup(left_id) : eval_expr(bin->left, current_bar, "");
        std::optional<double> right = right_id ? lookup(right_id) : eval_expr(bin->right, current_bar, "");

        if (!left.has_value() || !right.has_value()) return false;

        if (bin->op == "<") return left.value() < right.value();
        if (bin->op == ">") return left.value() > right.value();
        if (bin->op == "<=") return left.value() <= right.value();
        if (bin->op == ">=") return left.value() >= right.value();
        if (bin->op == "!=") return left.value() != right.value();

        if (bin->op == "crosses_above" || bin->op == "crosses_below") {
            if (!left_id || !right_id) return false;
            auto pl = prev_env.find(left_id->name);
            auto pr = prev_env.find(right_id->name);
            if (pl == prev_env.end() || pr == prev_env.end()) return false;

            if (bin->op == "crosses_above") {
                return pl->second <= pr->second && left.value() > right.value();
            } else {
                return pl->second >= pr->second && left.value() < right.value();
            }
        }

        throw std::runtime_error("Unknown operator: " + bin->op);
    }

public:
    Interpreter(std::vector<ASTNodePtr> prog) : program(std::move(prog)) {}

    std::vector<std::string> run_bar(const std::map<std::string, double>& bar) {
        prev_env = env;
        current_bar = bar;
        std::vector<std::string> signals;

        for (const auto& stmt : program) {
            if (auto a = std::dynamic_pointer_cast<Assignment>(stmt)) {
                std::optional<double> value = eval_expr(a->expression, bar, a->name);
                if (value.has_value()) {
                    env[a->name] = value.value();
                } else {
                    env.erase(a->name);
                }
            } else if (auto b = std::dynamic_pointer_cast<BuyStatement>(stmt)) {
                if (eval_condition_node(b->condition)) signals.push_back("BUY");
            } else if (auto s = std::dynamic_pointer_cast<SellStatement>(stmt)) {
                if (eval_condition_node(s->condition)) signals.push_back("SELL");
            }
        }

        return signals;
    }
};

#endif