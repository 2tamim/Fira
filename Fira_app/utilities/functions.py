
# Function calculates 3rd root of float number
def cube(x):
    if x >= 0:
        return x ** (1/3)
    elif x < 0:
        return -(abs(x) ** (1/3))

