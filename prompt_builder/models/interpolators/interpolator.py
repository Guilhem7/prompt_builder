"""
Shell-like String Interpolation Engine
=======================================
A rule-based tokenizer + AST evaluator that mimics Bash/Zsh prompt expansion.

Architecture:
  Lexer  = produces a flat list of Token objects
  Parser = consumes tokens and builds an AST
  Evaluator = walks the AST and resolves everything into a final string
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Callable, Dict, List, Optional, Tuple

@dataclasses.dataclass
class CommandRule:
    """Describes one command-substitution syntax, e.g. '$(' ... ')'."""
    start: str          # opening delimiter, e.g. "$("
    end: str            # closing delimiter, e.g. ")"

@dataclasses.dataclass
class ModeConfig:
    """Complete configuration for one syntax mode (Bash, Zsh, custom …)."""
    name: str
    escape_char: str                    # character that escapes the next token
    variable_prefix: str               # character that introduces a variable
    command_rules: List[CommandRule]    # ordered list of command-sub syntaxes

BASH_MODE = ModeConfig(
    name="bash",
    escape_char="\\",
    variable_prefix="\\",
    command_rules=[
        CommandRule(start="$(", end=")"),
    ],
)

ZSH_MODE = ModeConfig(
    name="zsh",
    escape_char="%",
    variable_prefix="%",
    command_rules=[
        CommandRule(start="$(", end=")"),
    ],
)

class TokenKind(enum.Enum):
    LITERAL     = "LITERAL"      # plain text, no special meaning
    ESCAPED     = "ESCAPED"      # escape_char + next_char  (e.g. "\\w")
    VARIABLE    = "VARIABLE"     # variable_prefix + key    (e.g. "\w")
    CMD_START   = "CMD_START"    # opening delimiter of a command sub
    CMD_CONTENT = "CMD_CONTENT"  # text between delimiters
    CMD_END     = "CMD_END"      # closing delimiter

@dataclasses.dataclass
class Token:
    kind: TokenKind
    value: str          # raw text captured by the token
    rule: Optional[CommandRule] = None   # set for CMD_START / CMD_END

class Lexer:
    """
    Scans the input string left-to-right and emits Token objects.

    Precedence (highest first):
      1. Escape sequence  (escape_char + any single char)
      2. Command-substitution start/end
      3. Variable reference (variable_prefix + single key char)
      4. Everything else = LITERAL
    """
    def __init__(self, config: ModeConfig) -> None:
        self.config = config

    def tokenize(self, text: str) -> List[Token]:
        tokens: List[Token] = []
        pos = 0
        n = len(text)
        # Track whether we are inside a command substitution and which rule.
        cmd_stack: List[Tuple[CommandRule, int]] = []
        esc = self.config.escape_char
        vp  = self.config.variable_prefix
        same = (esc == vp)

        while pos < n:
            ch = text[pos]

            # 1. Escape handling
            if ch == esc and pos + 1 < n:
                next_ch = text[pos + 1]
                if same:
                    # When escape_char == variable_prefix:
                    #   esc+esc  = literal escape_char  (true escape)
                    #   esc+alpha = variable (NOT an escape)
                    # Any other esc+X also acts as a true escape.
                    if next_ch == esc:
                        # doubled escape = literal escape char
                        tokens.append(Token(TokenKind.ESCAPED, text[pos: pos + 2]))
                        pos += 2
                        continue
                    # else: fall through to variable / literal handling
                else:
                    # escape_char != variable_prefix
                    # or a truly separate escape char:
                    # any esc+X is an escape sequence
                    tokens.append(Token(TokenKind.ESCAPED, text[pos: pos + 2]))
                    pos += 2
                    continue

            # 2. Command-substitution end (innermost open rule)
            if cmd_stack:
                active_rule, _ = cmd_stack[-1]
                end = active_rule.end
                if text[pos: pos + len(end)] == end:
                    tokens.append(Token(TokenKind.CMD_END, end, rule=active_rule))
                    cmd_stack.pop()
                    pos += len(end)
                    continue

            # 2b. Command-substitution start
            matched_cmd = False
            for rule in self.config.command_rules:
                start = rule.start
                if text[pos: pos + len(start)] == start:
                    tokens.append(Token(TokenKind.CMD_START, start, rule=rule))
                    cmd_stack.append((rule, pos))
                    pos += len(start)
                    matched_cmd = True
                    break

            if matched_cmd:
                continue

            # Inside a command sub = collect as CMD_CONTENT
            if cmd_stack:
                active_rule, _ = cmd_stack[-1]
                end = active_rule.end
                start_pos = pos
                while pos < n:
                    if text[pos] == esc and pos + 1 < n:
                        break
                    if text[pos: pos + len(end)] == end:
                        break
                    pos += 1
                if pos > start_pos:
                    tokens.append(Token(TokenKind.CMD_CONTENT, text[start_pos:pos]))
                continue

            # 3. Variable reference
            if ch == vp and pos + 1 < n and (text[pos + 1].isalpha() or text[pos + 1] in ("$", "~")):
                tokens.append(Token(TokenKind.VARIABLE, text[pos: pos + 2]))
                pos += 2
                continue

            # 4. Literal
            start_pos = pos
            while pos < n:
                c = text[pos]
                # Stop on escape (doubled escape when same=True)
                if c == esc and pos + 1 < n:
                    if same:
                        if text[pos + 1] == esc:
                            break   # doubled escape
                        # single esc+alpha = variable, stop here
                        if text[pos + 1].isalpha() or text[pos + 1] in ("$", "~"):
                            break
                    else:
                        break
                # Stop on cmd start
                found_cmd = False
                for rule in self.config.command_rules:
                    if text[pos: pos + len(rule.start)] == rule.start:
                        found_cmd = True
                        break
                if found_cmd:
                    break
                # Stop on variable prefix (only when not already handled above)
                if c == vp and pos + 1 < n and text[pos + 1].isalpha():
                    break
                # Stop on cmd-end when inside a sub
                if cmd_stack:
                    active_rule, _ = cmd_stack[-1]
                    if text[pos: pos + len(active_rule.end)] == active_rule.end:
                        break
                pos += 1

            if pos > start_pos:
                tokens.append(Token(TokenKind.LITERAL, text[start_pos:pos]))

        return tokens

class ASTNode:
    """Base class for all AST nodes."""


@dataclasses.dataclass
class LiteralNode(ASTNode):
    """A verbatim string fragment."""
    text: str

@dataclasses.dataclass
class EscapedNode(ASTNode):
    """An escaped character sequence — evaluates to the char after the escape."""
    raw: str          # the two-char escape sequence, e.g. "\\w"
    char: str         # the escaped character, e.g. "w"

@dataclasses.dataclass
class VariableNode(ASTNode):
    """A variable reference, e.g. \\w  or  %u."""
    key: str          # the single-char key, e.g. "w"

@dataclasses.dataclass
class CommandNode(ASTNode):
    """A command substitution, e.g. $(_get_git_branch)."""
    func_name: str    # the text inside the delimiters
    rule: CommandRule # which rule matched

@dataclasses.dataclass
class SequenceNode(ASTNode):
    """Root node — an ordered sequence of child nodes."""
    children: List[ASTNode]

class Parser:
    """
    Converts a flat token list into an AST.

    CMD_START … CMD_CONTENT … CMD_END  =  CommandNode
    VARIABLE                           =  VariableNode
    ESCAPED                            =  EscapedNode
    LITERAL                            =  LiteralNode
    """
    def __init__(self, config: ModeConfig) -> None:
        self.config = config

    def parse(self, tokens: List[Token]) -> SequenceNode:
        children: List[ASTNode] = []
        pos = 0

        while pos < len(tokens):
            tok = tokens[pos]

            if tok.kind == TokenKind.ESCAPED:
                # The escaped character is whatever follows the escape_char.
                escaped_char = tok.value[len(self.config.escape_char):]
                children.append(EscapedNode(raw=tok.value, char=escaped_char))
                pos += 1

            elif tok.kind == TokenKind.VARIABLE:
                key = tok.value[len(self.config.variable_prefix):]
                children.append(VariableNode(key=key))
                pos += 1

            elif tok.kind == TokenKind.CMD_START:
                rule = tok.rule
                pos += 1
                # Collect CMD_CONTENT tokens until matching CMD_END
                content_parts: List[str] = []
                while pos < len(tokens) and tokens[pos].kind != TokenKind.CMD_END:
                    if tokens[pos].kind == TokenKind.CMD_CONTENT:
                        content_parts.append(tokens[pos].value)
                    pos += 1
                # Consume CMD_END
                if pos < len(tokens) and tokens[pos].kind == TokenKind.CMD_END:
                    pos += 1
                func_name = "".join(content_parts).strip()
                children.append(CommandNode(func_name=func_name, rule=rule))

            elif tok.kind == TokenKind.LITERAL:
                children.append(LiteralNode(text=tok.value))
                pos += 1

            else:
                # Orphaned CMD_CONTENT or CMD_END (unclosed sub) = literal
                children.append(LiteralNode(text=tok.value))
                pos += 1

        return SequenceNode(children=children)

class Evaluator:
    """
    Walks a SequenceNode AST and resolves each node to a string.

    Resolution rules (in precedence order, already enforced by the lexer/parser):
      1. EscapedNode  = literal escaped character  (escape takes precedence)
      2. CommandNode  = call function registry; leave unchanged if not found
      3. VariableNode = look up in variable dict; leave unchanged if not found
      4. LiteralNode  = pass through as-is
    """
    def __init__(
        self,
        variables: Dict[str, str],
        functions: Dict[str, Callable[[], str]],
        config: ModeConfig,
    ) -> None:
        self.variables = variables
        self.functions = functions
        self.config = config

    def evaluate(self, node: ASTNode) -> str:
        if isinstance(node, SequenceNode):
            return "".join(self.evaluate(child) for child in node.children)

        if isinstance(node, LiteralNode):
            return node.text

        if isinstance(node, EscapedNode):
            # The escaped char is rendered literally, escape_char is consumed.
            return node.char

        if isinstance(node, VariableNode):
            if node.key in self.variables:
                return self.variables[node.key]
            # Unknown variable = keep original syntax
            return self.config.variable_prefix + node.key

        if isinstance(node, CommandNode):
            if node.func_name in self.functions:
                return self.functions[node.func_name]()
            # Unknown function, keep original syntax
            return node.rule.start + node.func_name + node.rule.end
        raise TypeError(f"Unknown AST node type: {type(node)}")

class InterpolationEngine:
    """
    High-level façade: Lexer = Parser = Evaluator in one call.

    Usage:
        engine = InterpolationEngine(
            config=BASH_MODE,
            variables={"w": "/home/alice", "u": "alice"},
            functions={"_get_git_branch": lambda: "main"},
        )
        result = engine.render("\\u at \\w on $(_get_git_branch)")
    """
    def __init__(
        self,
        config: ModeConfig,
        variables: Optional[Dict[str, str]] = None,
        functions: Optional[Dict[str, Callable[[], str]]] = None,
    ) -> None:
        self.config = config
        self.variables = variables or {}
        self.functions = functions or {}
        self._lexer = Lexer(config)
        self._parser = Parser(config)
        self._evaluator = Evaluator(self.variables, self.functions, config)

    def render(self, template: str) -> str:
        tokens = self._lexer.tokenize(template)
        ast    = self._parser.parse(tokens)
        return self._evaluator.evaluate(ast)

    def tokenize(self, template: str) -> List[Token]:
        return self._lexer.tokenize(template)

    def parse(self, template: str) -> SequenceNode:
        return self._parser.parse(self.tokenize(template))

if __name__ == '__main__':
    functions = {
        "_get_git_branch": lambda: "main",
        "_hostname":       lambda: "devbox",
        "_date":           lambda: "2026-06-02",
    }
    bash_vars = {"w": "/home/alice", "u": "alice", "n": "\n", "h": "localhost", "$": "$"}
    bash_engine = InterpolationEngine(
        config=BASH_MODE,
        variables=bash_vars,
        functions=functions,
    )

    ps1 = "\\u@\\w \\\\w $(_get_git_branch) >\n\\h \\A \\$ \\A "
    print(f"Original:\n{ps1}\n")
    print(f"Result:\n{bash_engine.render(ps1)}\n")

