from interesticker import INTEREST_TICKET

import requests

t = []

for item in INTEREST_TICKET:
    print(item)
    data = requests.get(
        url=f"https://api.kucoin.com/api/v1/market/candles?type=1day&symbol={item}"
    ).json()["data"][::-1]

    l = []

    ll = len(data)

    if ll != 100:
        l += [0 for _ in range(100 - ll)]
    for k in data:
        l.append(k[2])
    t.append(l)


percent = []

for i in t:
    e = []

    for index in range(len(i)):
        if i[index] != 0:
            if index != len(i) - 1:
                e.append(round(float(i[index + 1]) / float(i[index]) - 1, 3))
            else:
                continue
        else:
            e.append(0)

    percent.append(e)


day_percent = []

for i in range(99):
    s = 0
    for o in percent:
        s += o[i]
    day_percent.append(round(s / len(percent), 3))

print(t)
print(day_percent)
print(round(sum(day_percent), 3))

# [22.741, -15.652, -8.963, -20.807, 24.967, -20.156, 36.604, 15.211, -27.757, 14.97, -11.65, 10.707, 10.033, -8.118, -32.118, -3.811, 3.329, 1.048, -41.147, -7.414, 12.667, -5.951, 28.782, 7.485, -7.426, 16.594, -7.212, -23.757, -6.56, 3.658, -1.232, -6.883, 1.899, 1.661, 14.909, 6.4, 19.724, 3.807, 6.359, 19.556, -0.3, 28.068, 10.116, 4.362, -0.415, 21.689, 13.667, -9.153, -10.66, 11.216, -9.849, 23.022, 12.651, 20.692, 6.811, 9.971, 6.376, 44.817, 28.095, 12.246, 8.585, -34.901, 55.615, 24.264, 12.788, 40.455, 14.562, 32.02, 3.923, 24.659, -17.222, -30.633, -54.608, 46.335, -38.59, -52.375, 70.166, 0.011, -15.291, 13.123, 22.277, 30.671, -26.869, -6.562, 21.079, -0.831, -1.067, 17.084, -28.616, -40.651, -4.048, 16.183, -19.873, 16.002, 11.911, 21.148, -34.098, -2.048, -14.037]
# 330.46
