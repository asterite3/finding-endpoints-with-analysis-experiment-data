MARKERS = '''1_12c3b
1_25e2a
2_1f84b
2_2b7a3
3_45589
4_1c3f8
5_1e4d2
6_14b3c
7_16a9c
8_1b6e1
8_2b6f1
9_10ee31
9_11ee31
9_12ee31
9_13ee31
9_14ee31
9_15ee31
9_16ee31
9_17ee31
9_18ee31
9_19ee31
9_1a1b2
9_20ee31
9_21ee31
9_22ee31
9_23ee31
9_24ee31
9_25ee31
9_26dd2e
9_2ff21
9_3a2b7
9_4b82d
9_5ee31
9_6ee31
9_7ee31
9_8ee31
9_9ee31
10_17d77
11_1f2e4
11_2d3ff
12_1a2cf
12_2a2cf
12_3a2cf
13_10ad3
13_25af3
14_1eeab
15_1c95a
16_1b14f
16_2f41a
17_143ef
17_2da76
18_1a2f3
19_1f52a
19_2e3a2
20_1e833
21_1f822'''.splitlines()



def count_score_wivet(data, verbose=False):
    score = 0
    for m in MARKERS:
        m = '/innerpages/' + m + '.php'
        if any(m in r['url'] for r in data):
            score += 1
            if verbose:
                print('FOUND', m)
    return score

if __name__ == '__main__':
    import sys, json

    def do(f):
        data = json.load(f)
        score = count_score_wivet(data, True)
        print(score)

    if len(sys.argv) < 2:
        do(sys.stdin)
    else:
        with open(sys.argv[1]) as f:
            do(f)
