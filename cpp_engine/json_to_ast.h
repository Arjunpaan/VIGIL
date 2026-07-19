#include <fstream>
#ifndef JSON_TO_AST_H
#define JSON_TO_AST_H

#include "ast_nodes.h"
#include "json.hpp"
#include <stdexcept>

using json = nlohmann::json;

ASTNodePtr parse_node(const json& j) {
    std::string type = j["type"];

    if (type == "Identifier") {
        auto node = std::make_shared<Identifier>();
        node->name = j["name"];
        return node;
    }

    if (type == "NumberLiteral") {
        auto node = std::make_shared<NumberLiteral>();
        node->value = j["value"];
        return node;
    }

    if (type == "BinaryOp") {
        auto node = std::make_shared<BinaryOp>();
        node->left = parse_node(j["left"]);
        node->op = j["operator"];
        node->right = parse_node(j["right"]);
        return node;
    }

    if (type == "FunctionCall") {
        auto node = std::make_shared<FunctionCall>();
        node->name = j["name"];
        for (const auto& arg : j["args"]) {
            node->args.push_back(parse_node(arg));
        }
        return node;
    }

    if (type == "Assignment") {
        auto node = std::make_shared<Assignment>();
        node->name = j["name"];
        node->expression = parse_node(j["expression"]);
        return node;
    }

    if (type == "BuyStatement") {
        auto node = std::make_shared<BuyStatement>();
        node->condition = parse_node(j["condition"]);
        return node;
    }

    if (type == "SellStatement") {
        auto node = std::make_shared<SellStatement>();
        node->condition = parse_node(j["condition"]);
        return node;
    }

    throw std::runtime_error("Unknown node type: " + type);
}

std::vector<ASTNodePtr> load_program(const std::string& filepath) {
    std::ifstream file(filepath);
    json j;
    file >> j;

    std::vector<ASTNodePtr> program;
    for (const auto& stmt : j) {
        program.push_back(parse_node(stmt));
    }
    return program;
}

#endif