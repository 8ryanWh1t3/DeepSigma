"""Bounded interval arithmetic for explicitly normalized scalar calculations.

No eval/exec, attribute access, calls, indexing, or inferred units. The caller must
supply normalized variables and the dimensional model; the output is an enclosure,
not a distribution, and repeated-variable dependence may widen it.
"""
from __future__ import annotations
import ast
from fractions import Fraction
from .core import NumericRange
from .utils import number


def interval_calculate(expression: str,variables: dict[str,NumericRange],*,max_nodes=100):
    if not isinstance(expression,str) or not expression.strip() or len(expression)>2000:
        raise ValueError('expression must contain 1..2000 characters')
    if not isinstance(variables,dict) or len(variables)>100:
        raise ValueError('variables must be a bounded name/range mapping')
    if any(not isinstance(k,str) or not k.isidentifier() or not isinstance(v,NumericRange) for k,v in variables.items()):
        raise ValueError('variables must have identifier names and NumericRange values')
    for v in variables.values():
        if v.lower is None or v.upper is None:raise ValueError('interval arithmetic requires finite input bounds')
    try:tree=ast.parse(expression,mode='eval')
    except (SyntaxError,ValueError,RecursionError) as exc:raise ValueError('invalid bounded expression') from exc
    if sum(1 for _ in ast.walk(tree))>max_nodes:raise ValueError('expression exceeds syntax-node budget')
    def interval(lo,hi):return NumericRange(number(lo),number(hi))
    def walk(node):
        if isinstance(node,ast.Expression):return walk(node.body)
        if isinstance(node,ast.Name):
            if node.id not in variables:raise ValueError('missing variable: '+node.id)
            v=variables[node.id]
            if not v.lower_inclusive or not v.upper_inclusive:
                raise ValueError('calculator requires closed input intervals; normalize explicitly')
            return v
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            # Preserve exact decimal source syntax instead of binary float expansion.
            return NumericRange.point(ast.get_source_segment(expression,node))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            v=walk(node.operand)
            return v if isinstance(node.op,ast.UAdd) else interval(-v.upper,-v.lower)
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=walk(node.left),walk(node.right)
            if isinstance(node.op,ast.Add):return interval(a.lower+b.lower,a.upper+b.upper)
            if isinstance(node.op,ast.Sub):return interval(a.lower-b.upper,a.upper-b.lower)
            if isinstance(node.op,ast.Div):
                if b.lower<=0<=b.upper:raise ValueError('denominator interval includes zero')
                b=interval(1/b.upper,1/b.lower)
            products=[a.lower*b.lower,a.lower*b.upper,a.upper*b.lower,a.upper*b.upper]
            return interval(min(products),max(products))
        raise ValueError('only scalar names, numeric literals, unary signs, and + - * / are allowed')
    return walk(tree)
