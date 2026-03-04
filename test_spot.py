import spot

# Build FGa -> (GFb & GFc)
fga = spot.formula.F(spot.formula.G(spot.formula.ap("a")))
gfb = spot.formula.G(spot.formula.F(spot.formula.ap("b")));
gfc = spot.formula.G(spot.formula.F(spot.formula.ap("c")));
f = spot.formula.Implies(fga, spot.formula.And([gfb, gfc]));

print(f)

# kindstr() prints the name of the operator
# size() return the number of operands of the operators
print(f"{f.kindstr()}, {f.size()} children")
# [] accesses each operand
print(f"left: {f[0]}, right: {f[1]}")
# you can also iterate over all operands using a for loop
for child in f:
   print("  *", child)
# the type of the operator can be accessed with kind(), which returns
# an op_XXX constant (corresponding to the spot::op enum of C++)
print(f[1][0], "is F" if f[1][0].kind() == spot.op_F else "is not F")
# "is" is keyword in Python, the so shortcut is called _is:
print(f[1][1], "is G" if f[1][1]._is(spot.op_G) else "is not G")