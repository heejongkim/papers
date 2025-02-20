from analyse import *
import hoomd
import hoomd.md
import time
import os
import sys
from argparse import ArgumentParser
from mdtraj.utils.rotation import rotation_matrix_from_quaternion

parser = ArgumentParser()
parser.add_argument('--name',nargs='?',const='', type=str)
parser.add_argument('--ff',nargs='?',const='',type=str)
parser.add_argument('--run',nargs='?',const='',type=int)
args = parser.parse_args()

def simulate(residues,name,prot,ff,run):
    residues = residues.set_index('one')
    hoomd.context.initialize("--mode=gpu"); 
    hoomd.option.set_notice_level(0) 
    n_chains = 2
    pairs, lj_eps, lj_lambda, lj_sigma, fasta, types, MWs = genParamsLJ(residues,name,prot)
    yukawa_eps, yukawa_kappa = genParamsDH(residues,name,prot)
    N = len(fasta)
    L = 30
    xy = np.empty(0)
    xy = np.append(xy,np.random.rand(2)*L-L/2).reshape((-1,2))
    for x,y in np.random.rand(1000,2)*L-L/2:
        x1 = x-L if x>0 else x+L
        y1 = y-L if y>0 else y+L
        if np.all(np.linalg.norm(xy-[x,y],axis=1)>.9):
            if np.all(np.linalg.norm(xy-[x1,y],axis=1)>.9):
                if np.all(np.linalg.norm(xy-[x,y1],axis=1)>.9):
                    xy = np.append(xy,[x,y]).reshape((-1,2))
        if xy.shape[0] == n_chains:
            break

    snapshot = hoomd.data.make_snapshot(N=N*n_chains,
                                box=hoomd.data.boxdim(Lx=250, Ly=250, Lz=250),
                                particle_types=types,
                                bond_types=['polymer']);

    fst = ''.join(prot.fasta)

    snapshot.bonds.resize(n_chains*(N-1));

    for j,(x,y) in enumerate(xy):
        begin = j*N
        end = j*N+N
        
        snapshot.particles.position[begin:end] = [[x,y,(i-N/2.)*.38] for i in range(N)]
        snapshot.particles.typeid[begin:end] = [types.index(a) for a in fasta]
        snapshot.particles.mass[begin:end] = [residues.loc[a].MW for a in prot.fasta]
        snapshot.particles.mass[begin] += 2
        snapshot.particles.mass[end-1] += 16
    
        snapshot.bonds.group[begin-j:end-j-1] = [[i,i+1] for i in range(begin,end-1)];
        snapshot.bonds.typeid[begin-j:end-j-1] = [0] * (N-1)

    hoomd.init.read_snapshot(snapshot);

    kT = 8.3145*prot.temp*1e-3
    hb = hoomd.md.bond.harmonic();
    hb.bond_coeff.set('polymer', k=8033.0, r0=0.38);

    nl = hoomd.md.nlist.cell();

    lj1 = hoomd.md.pair.lj(r_cut=4.0, nlist=nl, name="one")
    lj2 = hoomd.md.pair.lj(r_cut=4.0, nlist=nl, name="two")
    yukawa = hoomd.md.pair.yukawa(r_cut=4.0, nlist=nl)
    for a,b in pairs:
        yukawa.pair_coeff.set(a, b, epsilon=yukawa_eps.loc[a,b], kappa=yukawa_kappa, r_cut=4.)
        lj1.pair_coeff.set(a, b, epsilon=lj_eps*(1-lj_lambda.loc[a,b]), sigma=lj_sigma.loc[a,b], 
                    r_cut=np.power(2.,1./6)*lj_sigma.loc[a,b])
        lj2.pair_coeff.set(a, b, epsilon=lj_eps*lj_lambda.loc[a,b], sigma=lj_sigma.loc[a,b], r_cut=4.)

    lj1.set_params(mode='shift')
    yukawa.set_params(mode='shift')
    nl.reset_exclusions(exclusions = ['bond'])

    integrator_mode = hoomd.md.integrate.mode_standard(dt=0.005);
    integrator = hoomd.md.integrate.langevin(group=hoomd.group.all(),kT=kT,seed=np.random.randint(100));
    for a,mw in zip(types,MWs):
        integrator.set_gamma(a, mw/100)
    # run to sample initial chain collapse to make chain fit into new box
    hoomd.run(2e5) 
    # update box size and start new run
    hoomd.update.box_resize(Lx=prot.L, Ly=prot.L, Lz=prot.L, period=None, scale_particles=False)
    dump = hoomd.dump.dcd(filename='{:s}/{:s}/run{:d}/prod.dcd'.format(name,ff,run), period=6e3,
                          group=hoomd.group.all(), 
                          overwrite=True, unwrap_full=True);
    hoomd.run(4e8) # 7e8
    genDCD(residues,name,prot,'{:s}/{:s}/run{:d}'.format(name,ff,run),'prod',n_chains)

residues = pd.read_csv('residues.csv').set_index('three',drop=False)
residues.lambdas = residues['M1']
proteins = pd.read_pickle('proteins.pkl')

t0 = time.time()
simulate(residues,args.name,proteins.loc[args.name],args.ff,args.run)
print('Timing {:.3f}'.format(time.time()-t0))
