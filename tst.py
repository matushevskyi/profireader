N, S, p, m, r, h = list(map(int, input().split())) + [print, map, str, list]

class segment:
    x = 0
    y = 0
    ind = 0

    def __init__(self, x, y, ind):
        self.x = x
        self.y = y
        self.ind = ind

    def diff(self, s):
        return segment(max(self.x, s.x), min(self.y, s.y), self.ind + s.ind)

    def __repr__(self):
        return "%s->%s [%s]" % (str(self.x), str(self.y), ', '.join(map(str, self.ind)))


def wo(a, i):
    return a[:i] + a[i + 1:]


def f(a, el):
    # print('entering element', el)
    # print('entering array', a)
    # print('')

    if (el and el.y - el.x == S):
        print(r(len(el.ind)) + "\n" + ' '.join(map(r, el.ind)), end = '')
        return True

    for i, cur in enumerate(a):
        if el and f(wo(a, i), el.diff(cur)):
            return True
        if f(wo(a, i), cur):
            return True

    return False


ll = [list(map(int, input().split())) for __ in range(N)]
ll = [segment(l[0], l[1], [i + 1]) for i, l in enumerate(ll)]
f(ll, None)
