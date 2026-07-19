#ifndef AST_NODES_H
#define AST_NODES_H

#include <string>
#include <vector>
#include <memory>

// Base class — every node type inherits from this
struct ASTNode {
    virtual ~ASTNode() = default;
};

using ASTNodePtr = std::shared_ptr<ASTNode>;

struct Identifier : ASTNode {
    std::string name;
};

struct NumberLiteral : ASTNode {
    double value;
};

struct BinaryOp : ASTNode {
    ASTNodePtr left;
    std::string op;
    ASTNodePtr right;
};

struct FunctionCall : ASTNode {
    std::string name;
    std::vector<ASTNodePtr> args;
};

struct Assignment : ASTNode {
    std::string name;
    ASTNodePtr expression;
};

struct BuyStatement : ASTNode {
    ASTNodePtr condition;
};

struct SellStatement : ASTNode {
    ASTNodePtr condition;
};

#endif