"""Design-based estimation helpers for BAHDA-2026 Paper 15.

Implements the estimators that Stata's `svy:` prefix uses with a stratified
design (Taylor-series linearisation, with-replacement PSU variance within
strata), so that results can be reproduced with
`svyset psu [pw=survey_weight], strata(sampling_stratum)` in Stata.
"""
import numpy as np
import pandas as pd
from scipy import optimize, stats


# --------------------------------------------------------------------------
# Linearisation variance
# --------------------------------------------------------------------------
def design_meat(scores, strata, psu):
    """Stratified between-PSU covariance of score/influence totals.

    scores : (n, k) array of observation-level weighted scores
    Returns G = sum_h n_h/(n_h-1) sum_j (z_hj - zbar_h)(z_hj - zbar_h)'.
    """
    scores = np.asarray(scores, float)
    if scores.ndim == 1:
        scores = scores[:, None]
    df = pd.DataFrame(scores)
    df["_h"] = np.asarray(strata)
    df["_p"] = np.asarray(psu)
    k = scores.shape[1]
    G = np.zeros((k, k))
    for _, sub in df.groupby("_h"):
        tot = sub.groupby("_p")[list(range(k))].sum().to_numpy()
        nh = tot.shape[0]
        if nh < 2:
            continue
        d = tot - tot.mean(0)
        G += nh / (nh - 1) * d.T @ d
    return G


def design_df(strata, psu):
    """Design degrees of freedom: number of PSUs minus number of strata."""
    s = pd.DataFrame({"h": np.asarray(strata), "p": np.asarray(psu)})
    return s.drop_duplicates().shape[0] - s["h"].nunique()


# --------------------------------------------------------------------------
# Weighted proportions and means
# --------------------------------------------------------------------------
def svy_prop(y, w, strata, psu, levels):
    """Weighted proportions with logit-transformed 95% CIs (as Stata svy: tab)."""
    y = np.asarray(y)
    w = np.asarray(w, float)
    W = w.sum()
    dfd = design_df(strata, psu)
    t = stats.t.ppf(0.975, dfd)
    out = []
    for lv in levels:
        z = (y == lv).astype(float)
        p = (w * z).sum() / W
        u = w * (z - p) / W
        se = np.sqrt(design_meat(u, strata, psu)[0, 0])
        if 0 < p < 1:
            lse = se / (p * (1 - p))
            lo = 1 / (1 + np.exp(-(np.log(p / (1 - p)) - t * lse)))
            hi = 1 / (1 + np.exp(-(np.log(p / (1 - p)) + t * lse)))
        else:
            lo = hi = p
        out.append(dict(level=lv, n=int(z.sum()), wn=(w * z).sum(), p=p, se=se, lo=lo, hi=hi))
    return pd.DataFrame(out)


def svy_mean(x, w, strata, psu):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    W = w.sum()
    m = (w * x).sum() / W
    u = w * (x - m) / W
    se = np.sqrt(design_meat(u, strata, psu)[0, 0])
    t = stats.t.ppf(0.975, design_df(strata, psu))
    sd = np.sqrt((w * (x - m) ** 2).sum() / W)
    return dict(mean=m, se=se, lo=m - t * se, hi=m + t * se, wsd=sd)


def rao_scott(x, y, w, strata, psu):
    """First-order Rao-Scott corrected Pearson chi-square for an R x C table.

    Returns F statistic, numerator df, denominator df, p value and mean
    generalised design effect.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    w = np.asarray(w, float)
    rl = np.unique(x)
    cl = np.unique(y)
    R, C = len(rl), len(cl)
    n = len(x)
    W = w.sum()
    Z = np.zeros((n, R * C))
    for i, a in enumerate(rl):
        for j, b in enumerate(cl):
            Z[:, i * C + j] = (x == a) & (y == b)
    p = (w[:, None] * Z).sum(0) / W
    U = w[:, None] * (Z - p) / W
    V = design_meat(U, strata, psu)
    P = p.reshape(R, C)
    pr, pc = P.sum(1), P.sum(0)
    E = np.outer(pr, pc)
    X2 = n * ((P - E) ** 2 / np.where(E > 0, E, np.nan)).sum()
    # interaction residuals h_rc = p_rc - p_r. p_.c for r<R, c<C
    idx = [(i, j) for i in range(R - 1) for j in range(C - 1)]
    J = np.zeros((len(idx), R * C))
    for k, (i, j) in enumerate(idx):
        for a in range(R):
            for b in range(C):
                d = (a == i and b == j) * 1.0
                if a == i:
                    d -= pc[j]
                if b == j:
                    d -= pr[i]
                J[k, a * C + b] = d
    p0 = E.ravel()
    V0 = (np.diag(p0) - np.outer(p0, p0)) / n
    A = J @ V0 @ J.T
    B = J @ V @ J.T
    dfn = (R - 1) * (C - 1)
    deff = np.trace(np.linalg.pinv(A) @ B) / dfn
    dfd = design_df(strata, psu)
    F = X2 / deff / dfn
    pval = stats.f.sf(F, dfn, dfn * dfd)
    return dict(X2=X2, deff=deff, F=F, df1=dfn, df2=dfn * dfd, p=pval)


def svy_anova(xcont, groups, w, strata, psu):
    """Design-based Wald F test that a continuous variable's weighted mean is
    equal across groups (svy: regress x i.group; testparm i.group)."""
    g = pd.Categorical(groups)
    X = np.column_stack([np.ones(len(g))] + [(g.codes == k).astype(float) for k in range(1, len(g.categories))])
    y = np.asarray(xcont, float)
    w = np.asarray(w, float)
    XtWX = X.T @ (w[:, None] * X)
    b = np.linalg.solve(XtWX, X.T @ (w * y))
    e = y - X @ b
    S = w[:, None] * X * e[:, None]
    Hinv = np.linalg.inv(XtWX)
    V = Hinv @ design_meat(S, strata, psu) @ Hinv
    q = X.shape[1] - 1
    bb = b[1:]
    Vb = V[1:, 1:]
    Wst = bb @ np.linalg.solve(Vb, bb)
    d = design_df(strata, psu)
    # unadjusted Wald F with residual design df, as R survey::regTermTest
    F = Wst / q
    return dict(F=F, df1=q, df2=d - q, p=stats.f.sf(F, q, d - q))


# --------------------------------------------------------------------------
# Survey-weighted multinomial logit
# --------------------------------------------------------------------------
class SvyMlogit:
    """Pseudo-maximum-likelihood multinomial logit with linearised variance.

    y   : integer outcome codes; `base` is the reference category
    X   : DataFrame of predictors (constant added internally)
    ridge : optional L2 penalty on slopes (0 = ordinary pseudo-ML)
    """

    def __init__(self, y, X, w, strata, psu, base=0, ridge=0.0):
        self.levels = sorted(np.unique(y))
        self.base = base
        self.alts = [l for l in self.levels if l != base]
        self.Xdf = X
        self.X = np.column_stack([np.ones(len(X)), X.to_numpy(float)])
        self.names = ["_cons"] + list(X.columns)
        self.y = np.asarray(y)
        self.w = np.asarray(w, float)
        self.strata = np.asarray(strata)
        self.psu = np.asarray(psu)
        self.ridge = ridge
        self.Y = np.column_stack([(self.y == a).astype(float) for a in self.alts])

    def _probs(self, beta, X=None):
        X = self.X if X is None else X
        B = beta.reshape(len(self.alts), X.shape[1])
        eta = X @ B.T
        m = np.maximum(eta.max(1), 0)
        ex = np.exp(eta - m[:, None])
        den = np.exp(-m) + ex.sum(1)
        return ex / den[:, None], np.exp(-m) / den

    def _pen_mask(self):
        k = self.X.shape[1]
        m = np.ones((len(self.alts), k))
        m[:, 0] = 0
        return m.ravel()

    def nll(self, beta):
        P, P0 = self._probs(beta)
        lp = np.where(self.Y.sum(1) == 1, np.log((self.Y * P).sum(1) + 1e-300), np.log(P0 + 1e-300))
        pen = 0.5 * self.ridge * np.sum(self._pen_mask() * beta ** 2)
        return -(self.w * lp).sum() + pen

    def grad(self, beta):
        P, _ = self._probs(beta)
        R = (self.Y - P) * self.w[:, None]
        g = (R.T @ self.X).ravel()
        return -g + self.ridge * self._pen_mask() * beta

    def hessian(self, beta):
        P, _ = self._probs(beta)
        J, k = len(self.alts), self.X.shape[1]
        H = np.zeros((J * k, J * k))
        Xw = self.X * self.w[:, None]
        for a in range(J):
            for b in range(J):
                c = P[:, a] * ((a == b) - P[:, b])
                H[a * k:(a + 1) * k, b * k:(b + 1) * k] = (Xw * c[:, None]).T @ self.X
        return H + np.diag(self.ridge * self._pen_mask())

    def fit(self, maxiter=200, tol=1e-10):
        J, k = len(self.alts), self.X.shape[1]
        beta = np.zeros(J * k)
        # Newton-Raphson with step halving
        f0 = self.nll(beta)
        self.converged = False
        for it in range(maxiter):
            g = self.grad(beta)
            H = self.hessian(beta)
            step = np.linalg.solve(H + 1e-12 * np.eye(len(beta)), g)
            s = 1.0
            while s > 1e-8:
                nb = beta - s * step
                f1 = self.nll(nb)
                if f1 <= f0 + 1e-12:
                    break
                s /= 2
            beta, fold, f0 = nb, f0, f1
            if abs(fold - f0) < tol * (1 + abs(f0)) and np.max(np.abs(g)) < 1e-5 * (1 + abs(f0)):
                self.converged = True
                break
        self.iterations = it + 1
        self.beta = beta
        self.ll = -self.nll(beta) if self.ridge == 0 else -(self.nll(beta) - 0.5 * self.ridge * np.sum(self._pen_mask() * beta ** 2))
        # Parameters drifting to +/-infinity indicate (quasi-)complete separation,
        # e.g. an empty predictor-by-outcome cell. They are reported as not
        # estimable and excluded from the variance calculation.
        self.separated = np.abs(beta) > 10
        keep = ~self.separated
        P, _ = self._probs(beta)
        S = np.einsum("ij,ik->ijk", (self.Y - P) * self.w[:, None], self.X).reshape(len(self.y), -1)
        self.scores = S
        H = self.hessian(beta)
        Hinv = np.linalg.inv(H[np.ix_(keep, keep)])
        Vk = Hinv @ design_meat(S[:, keep], self.strata, self.psu) @ Hinv
        self.V = np.full((len(beta), len(beta)), 0.0)
        self.V[np.ix_(keep, keep)] = Vk
        self.V_model = np.zeros_like(self.V)
        self.V_model[np.ix_(keep, keep)] = Hinv
        self.dfd = design_df(self.strata, self.psu)
        self.se = np.where(keep, np.sqrt(np.abs(np.diag(self.V))), np.nan)
        # null (intercept-only) pseudo-log-likelihood
        wp = np.array([(self.w * (self.y == l)).sum() for l in self.levels]) / self.w.sum()
        self.ll0 = sum((self.w * (self.y == l)).sum() * np.log(wp[i]) for i, l in enumerate(self.levels))
        self.k = len(beta)
        return self

    # ---- summaries -------------------------------------------------------
    def table(self):
        t = stats.t.ppf(0.975, self.dfd)
        rows = []
        k = self.X.shape[1]
        for a_i, a in enumerate(self.alts):
            for j, nm in enumerate(self.names):
                b = self.beta[a_i * k + j]
                se = self.se[a_i * k + j]
                tv = b / se
                sep = bool(self.separated[a_i * k + j])
                rows.append(dict(outcome=a, term=nm, b=b, se=se, rrr=np.exp(b), lo=np.exp(b - t * se),
                                 hi=np.exp(b + t * se), t=tv, p=2 * stats.t.sf(abs(tv), self.dfd),
                                 separated=sep))
        return pd.DataFrame(rows)

    def wald(self, cols):
        """Adjusted Wald F test that all coefficients on `cols` are zero in every equation."""
        k = self.X.shape[1]
        idx = [a * k + self.names.index(c) for a in range(len(self.alts)) for c in cols
               if not self.separated[a * k + self.names.index(c)]]
        b = self.beta[idx]
        V = self.V[np.ix_(idx, idx)]
        q = len(idx)
        Wst = b @ np.linalg.solve(V, b)
        d = self.dfd
        F = (d - q + 1) / (d * q) * Wst
        return dict(F=F, df1=q, df2=d - q + 1, p=stats.f.sf(F, q, d - q + 1))

    def predict(self, X=None, beta=None):
        beta = self.beta if beta is None else beta
        if X is not None:
            X = np.column_stack([np.ones(len(X)), X.to_numpy(float)])
        P, P0 = self._probs(beta, X)
        out = np.zeros((len(P0), len(self.levels)))
        bi = self.levels.index(self.base)
        out[:, bi] = P0
        for a_i, a in enumerate(self.alts):
            out[:, self.levels.index(a)] = P[:, a_i]
        return out

    def info(self):
        n = len(self.y)
        return dict(n=n, ll=self.ll, ll0=self.ll0, k=self.k, aic=-2 * self.ll + 2 * self.k,
                    bic=-2 * self.ll + np.log(n) * self.k, r2_mcf=1 - self.ll / self.ll0,
                    dfd=self.dfd, converged=self.converged, iterations=self.iterations)


def margins(model, setter_list, labels):
    """Survey-weighted average adjusted predictions with delta-method CIs.

    setter_list: list of functions taking a copy of the predictor DataFrame and
    returning the counterfactual DataFrame (e.g. everybody set to Urban).
    Returns predicted probabilities for every outcome level and scenario,
    plus the gradient so contrasts can be formed.
    """
    w = model.w / model.w.sum()
    res = {}
    for lab, f in zip(labels, setter_list):
        Xc = f(model.Xdf.copy())
        Xm = np.column_stack([np.ones(len(Xc)), Xc.to_numpy(float)])

        def ap(beta, Xm=Xm):
            P, P0 = model._probs(beta, Xm)
            full = np.zeros((len(P0), len(model.levels)))
            full[:, model.levels.index(model.base)] = P0
            for a_i, a in enumerate(model.alts):
                full[:, model.levels.index(a)] = P[:, a_i]
            return w @ full

        est = ap(model.beta)
        eps = 1e-6
        G = np.zeros((len(est), len(model.beta)))
        for j in range(len(model.beta)):
            bp = model.beta.copy()
            bp[j] += eps
            G[:, j] = (ap(bp) - est) / eps
        res[lab] = (est, G)
    return res


def contrast(model, mres, a, b):
    """AME of scenario a minus scenario b for each outcome level, with CI and p."""
    ea, Ga = mres[a]
    eb, Gb = mres[b]
    d = ea - eb
    G = Ga - Gb
    V = G @ model.V @ G.T
    se = np.sqrt(np.diag(V))
    t = stats.t.ppf(0.975, model.dfd)
    p = 2 * stats.t.sf(np.abs(d / se), model.dfd)
    return pd.DataFrame(dict(level=model.levels, ame=d, se=se, lo=d - t * se, hi=d + t * se, p=p))


def level_ci(model, mres, a):
    e, G = mres[a]
    V = G @ model.V @ G.T
    se = np.sqrt(np.diag(V))
    t = stats.t.ppf(0.975, model.dfd)
    return pd.DataFrame(dict(level=model.levels, pr=e, se=se, lo=e - t * se, hi=e + t * se))


def svychisq_f(x, y, w, strata, psu):
    """Rao-Scott second-order (Satterthwaite) F test for an R x C table,
    as in R survey::svychisq(statistic = "F")."""
    x = np.asarray(x)
    y = np.asarray(y)
    w = np.asarray(w, float)
    rl, cl = np.unique(x), np.unique(y)
    R, C = len(rl), len(cl)
    n = len(x)
    W = w.sum()
    # cells ordered with rows varying fastest, as expand.grid in R
    Z = np.column_stack([(x == a) & (y == b) for b in cl for a in rl]).astype(float)
    m = (w[:, None] * Z).sum(0) / W
    V = design_meat(w[:, None] * (Z - m) / W, strata, psu)
    rows = np.tile(np.arange(R), C)
    cols = np.repeat(np.arange(C), R)
    X1 = np.column_stack([np.ones(R * C)] + [(rows == i) * 1.0 for i in range(1, R)]
                         + [(cols == j) * 1.0 for j in range(1, C)])
    X12 = np.column_stack([(rows == i) * (cols == j) * 1.0 for j in range(1, C) for i in range(1, R)])
    Cm = X12 - X1 @ np.linalg.lstsq(X1, X12, rcond=None)[0]
    iD = np.diag(np.where(m > 0, 1 / np.where(m > 0, m, 1), 0))
    denom = Cm.T @ (iD / n) @ Cm
    numr = Cm.T @ iD @ V @ iD @ Cm
    Delta = np.linalg.solve(denom, numr)
    P = m.reshape(C, R).T
    E = np.outer(P.sum(1), P.sum(0))
    X2 = n * ((P - E) ** 2 / np.where(E > 0, E, np.nan)).sum()
    tr = np.trace(Delta)
    d0 = tr ** 2 / np.trace(Delta @ Delta)
    F = X2 / tr
    nu = design_df(strata, psu)
    return dict(X2=X2, F=F, df1=d0, df2=d0 * nu, p=stats.f.sf(F, d0, d0 * nu))
