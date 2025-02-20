import numpy as np
import scipy.stats as scs
from sklearn.linear_model import LinearRegression
import mdtraj as md
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap, LinearSegmentedColormap

new_cmap = ['#DC0000','#DC2900','#DC6100','#DC8F00','#DCCC00','#CFDC00','#2ADC00','#114E00']
rtg_r = LinearSegmentedColormap.from_list("rtg", new_cmap)
new_cmap.reverse()
rtg = LinearSegmentedColormap.from_list("rtg", new_cmap)

dro = np.arange(-8.0,21.1,1.0)*3.34
r0 = np.arange(0.85,1.11,0.025)
yt = []
for i,x in enumerate(r0):
    if not (i+1)%2 == 0:
        yt.append('%.3f'%(x))
xt = []
for i,x in enumerate(dro):
    if not (i+1)%2 == 0:
        xt.append('%.2f'%(x))

def kld(p,q):
    p[p==0] = 1e-50
    q[q==0] = 1e-50
    div = scs.entropy(p,q)
    div = np.exp(-div)
    return(div)

def grid_entropy(grid, wdir, minind):
    div = []
    w_best = np.loadtxt(wdir+'w'+str(minind)+'.dat')[...,1]
    for i in grid:
        gind = str(int(i[0]))
        if i[3] != np.inf:
            w = np.loadtxt(wdir+'w'+gind+'.dat')[...,1]
            div.append(kld(w_best,w))
        else:
            div.append(np.inf)
    return np.array(div)

def minfind(grid):
    minind = np.where(grid[...,6] == np.nanmin(grid[...,6]))[0][0]
    mindro = grid[...,1][minind]*3.34
    minr0 = grid[...,2][minind]
    return int(minind), mindro, minr0

def rg_kde(rg,w):
    av = np.average(rg,weights=w)
    x = np.linspace( rg.min()-0.5, rg.max()+0.5, num = 200 )
    kde = scs.gaussian_kde( rg, bw_method = "silverman", weights = w ).evaluate(x)
    return np.array([x,kde,av])


def good_fit(slope,intercept,x,y,err):
    store = 0
    for i in range(len(x)):
        r = (slope*x[i])+intercept
        store = store + ((r-y[i])/err[i])**2
    return store/len(x)


def guinier_scan(expf,cut,start,end):

    sRg = []
    Rg = []
    score = []

    q = expf[...,0]
    exp = expf[...,1]
    err = expf[...,2]

    for i in range(start,end):
        guinier_q = q[cut:i]**2
        guinier_i = np.log(exp[cut:i])
        guinier_err = err[cut:i]/exp[cut:i]
        model = LinearRegression()
        model.fit(guinier_q.reshape(-1,1),guinier_i,(1/guinier_err))
    
        a = model.coef_[0]
        b = model.intercept_
    
        score.append(good_fit(a,b,guinier_q,guinier_i,guinier_err))
    
        rg = np.sqrt(-a*3)
        Rg.append(rg)
        sRg.append(rg*q[i])

        if sRg[-1] >= 1.8:
            break

    return sRg, Rg, score

def rg_calc_mass(path,size):
    rg = []
    for i in range(size):
        conf=md.load(path+"/frame"+str(i)+".pdb")
        mass = np.array([a.element.mass for a in conf.top.atoms])
        rg.append(md.compute_rg(conf,masses=mass))
    return np.array(rg)


volume = {'carbon': 16.44,
         'nitrogen': 2.49,
         'oxygen': 9.13,
         'hydrogen': 5.15,
         'sulfur': 25.31}
electrons = {'carbon': 6,
         'nitrogen': 7,
         'oxygen': 8,
         'hydrogen': 1,
         'sulfur': 16}
d_h2o = 0.334
d_atoms = {}
for k,v in volume.items():
    d_atoms[k] = electrons[k]/v
atomic_contrast = {}
for k,v in d_atoms.items():
    atomic_contrast[k] = (v-d_h2o)**2

def rg_calc_contrast(path,size):
    rg = []
    for i in range(size):
        conf=md.load(path+"/frame"+str(i)+".pdb")
        contrast = np.array([atomic_contrast[str(a.element)] for a in conf.top.atoms])
        rg.append(md.compute_rg(conf,masses=contrast))
    return np.array(rg)
