def calculate_bmi(weight, height):
    return weight / (height ** 2)

def calculate_body_fat(bmi, age, gender):
    if gender == "male":
        return (1.20 * bmi) + (0.23 * age) - 16.2
    elif gender == "female":
        return (1.20 * bmi) + (0.23 * age) - 5.4
    else:
        return None