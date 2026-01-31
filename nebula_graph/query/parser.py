# -*- coding: utf-8 -*-
"""
nebula_graph.query.parser
~~~~~~~~~~~~~~~~~~~~~~~~~

Parser języka zapytań grafowych (GQL).
Implementuje podzbiór składni Cypher (OpenCypher).

Supported Syntax:
    MATCH (n:Label) WHERE n.prop = 'value' RETURN n

Phases:
    1. Lexical Analysis (Tokenizacja): Rozbijanie stringa na tokeny (KEYWORD, IDENTIFIER, LITERAL).
    2. Syntactic Analysis (Parsing): Budowanie drzewa AST (Abstract Syntax Tree).
    3. Query Plan Generation: Przekształcenie AST w wykonywalny plan.

Architektura:
    - Recursive Descent Parser (prosty w implementacji ręcznej bez generatorów parserów typu ANTLR).
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# --- AST Nodes ---

@dataclass
class QueryNode:
    """Bazowa klasa węzła AST."""
    pass

@dataclass
class MatchClause(QueryNode):
    variable: str
    labels: List[str]
    properties: Dict[str, Any]

@dataclass
class WhereClause(QueryNode):
    variable: str
    property_name: str
    operator: str # '=', '>', '<'
    value: Any

@dataclass
class ReturnClause(QueryNode):
    variable: str

@dataclass
class QueryAST:
    matches: List[MatchClause]
    where: Optional[WhereClause]
    returns: List[ReturnClause]


# --- Lexer ---

class TokenType:
    KEYWORD = "KEYWORD"
    IDENTIFIER = "ID"
    SYMBOL = "SYMBOL"
    STRING = "STRING"
    NUMBER = "NUMBER"
    EOF = "EOF"

@dataclass
class Token:
    type: str
    value: str
    position: int

class Lexer:
    """Prosty tokenizator regexowy."""
    
    PATTERNS = [
        (TokenType.KEYWORD, r'\b(MATCH|WHERE|RETURN|AND|OR)\b'),
        (TokenType.NUMBER, r'\b\d+\.?\d*\b'),
        (TokenType.STRING, r"'[^']*'|\"[^\"]*\""),
        (TokenType.IDENTIFIER, r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
        (TokenType.SYMBOL, r'[\(\)\:\.\=\-\>\[\]\{\}]'),
        (TokenType.EOF, r'$'), # Koniec
    ]

    def tokenize(self, text: str) -> List[Token]:
        tokens = []
        pos = 0
        while pos < len(text):
            if text[pos].isspace():
                pos += 1
                continue
            
            match = None
            for token_type, pattern in self.PATTERNS:
                regex = re.compile(pattern, re.IGNORECASE)
                m = regex.match(text, pos)
                if m:
                    val = m.group(0)
                    # Cleaning quotes
                    if token_type == TokenType.STRING:
                        val = val[1:-1]
                    # Casting numbers
                    if token_type == TokenType.NUMBER:
                        val = float(val) if '.' in val else int(val)
                        
                    tokens.append(Token(token_type, val, pos))
                    pos = m.end()
                    match = m
                    break
            
            if not match:
                raise SyntaxError(f"Illegal character at position {pos}: {text[pos]}")
                
        return tokens


# --- Parser ---

class QueryParser:
    """Recursive Descent Parser dla GQL."""
    
    def __init__(self, query_text: str):
        self.lexer = Lexer()
        self.tokens = self.lexer.tokenize(query_text)
        self.pos = 0

    def parse(self) -> QueryAST:
        # Podstawowa struktura: MATCH ... [WHERE ...] RETURN ...
        matches = []
        where = None
        returns = []

        # 1. Parse MATCH
        if self._match("KEYWORD", "MATCH"):
            matches.append(self._parse_pattern())
        else:
            raise SyntaxError("Query must start with MATCH")

        # 2. Parse WHERE (Optional)
        if self._peek("KEYWORD", "WHERE"):
            self._advance()
            where = self._parse_where()

        # 3. Parse RETURN
        if self._match("KEYWORD", "RETURN"):
            returns.append(self._parse_return())
        else:
            raise SyntaxError("Query must have RETURN clause")

        return QueryAST(matches, where, returns)

    # --- Recursive Rules ---

    def _parse_pattern(self) -> MatchClause:
        # Pattern: (var:Label)
        self._expect("SYMBOL", "(")
        var_name = self._expect("ID").value
        
        labels = []
        if self._match("SYMBOL", ":"):
            labels.append(self._expect("ID").value)
        
        props = {} # TODO: Parsowanie {key: val}
        
        self._expect("SYMBOL", ")")
        return MatchClause(var_name, labels, props)

    def _parse_where(self) -> WhereClause:
        # WHERE var.prop = val
        var_name = self._expect("ID").value
        self._expect("SYMBOL", ".")
        prop_name = self._expect("ID").value
        
        op = self._expect("SYMBOL", "=").value # Na razie tylko równość
        
        val_token = self._current()
        if val_token.type not in (TokenType.STRING, TokenType.NUMBER):
            raise SyntaxError("Expected literal value")
        self._advance()
        
        return WhereClause(var_name, prop_name, op, val_token.value)

    def _parse_return(self) -> ReturnClause:
        var_name = self._expect("ID").value
        return ReturnClause(var_name)

    # --- Helper methods ---

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "", -1)

    def _peek(self, type_: str, val: str = None) -> bool:
        tk = self._current()
        if tk.type != type_: return False
        if val and tk.value.upper() != val.upper() and isinstance(tk.value, str): return False
        return True

    def _match(self, type_: str, val: str = None) -> bool:
        if self._peek(type_, val):
            self._advance()
            return True
        return False

    def _expect(self, type_: str, val: str = None) -> Token:
        if self._match(type_, val):
            return self.tokens[self.pos - 1]
        raise SyntaxError(f"Expected {type_}:{val}, got {self._current()}")

    def _advance(self):
        self.pos += 1
