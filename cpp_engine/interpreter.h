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

    bool eval_condition(const std::shared_ptr<BinaryOp>& node) {
        auto left_id = std::dynamic_pointer_cast<Identifier>(node->left);
        auto right_id = std::dynamic_pointer_cast<Identifier>(node->right);

        std::optional<double> left = left_id ? 
            (env.find(left_id->name) != env.end() ? std::optional<double>(env.at(left_id->name)) : std::nullopt)
            : eval_expr(node->left, {}, "");

        std::optional<double> right;
        if (right_id) {
            right = (env.find(right_id->name) != env.end()) ? std::optional<double>(env.at(right_id->name)) : std::nullopt;
        } else {
            right = eval_expr(node->right, {}, "");
        }

        if (!left.has_value() || !right.has_value()) return false;

        if (node->op == "<") return left.value() < right.value();
        if (node->op == ">") return left.value() > right.value();

        if (node->op == "crosses_above" || node->op == "crosses_below") {
            if (!left_id || !right_id) return false;
            auto pl = prev_env.find(left_id->name);
            auto pr = prev_env.find(right_id->name);
            if (pl == prev_env.end() || pr == prev_env.end()) return false;

            if (node->op == "crosses_above") {
                return pl->second <= pr->second && left.value() > right.value();
            } else {
                return pl->second >= pr->second && left.value() < right.value();
            }
        }

        throw std::runtime_error("Unknown operator: " + node->op);
    }

public:
    Interpreter(std::vector<ASTNodePtr> prog) : program(std::move(prog)) {}

    std::vector<std::string> run_bar(const std::map<std::string, double>& bar) {
        prev_env = env;
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
                auto cond = std::dynamic_pointer_cast<BinaryOp>(b->condition);
                if (eval_condition(cond)) signals.push_back("BUY");
            } else if (auto s = std::dynamic_pointer_cast<SellStatement>(stmt)) {
                auto cond = std::dynamic_pointer_cast<BinaryOp>(s->condition);
                if (eval_condition(cond)) signals.push_back("SELL");
            }
        }

        return signals;
    }
};

#endif