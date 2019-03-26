import numpy as np


class PSO:
    def __init__(self, objfunc, num, lb, ub):
        lb = np.array(lb)
        ub = np.array(ub)
        self.lb = lb
        self.ub = ub
        self.particles = lb + np.random.random((num, lb.size)) * (ub - lb)
        self.pbest = self.particles.copy()

        # Init evaluate
        self.objfunc = objfunc
        self.scores = np.array(self.evaluate())

        self.pbest_score = self.scores.copy()
        self.global_best = self.particles[np.argmin(self.scores)].copy()
        self.global_best_score = np.min(self.scores)

        self.pvel = np.random.random((num, lb.size)) * 2 * (np.abs(ub - lb)) - np.abs(ub - lb)

    def evaluate(self):
        scores = []
        for i in self.particles:
            scores.append(self.objfunc(i))
        return scores

    def run(self, n_iter=10, keep_data=False, verbose=True, callback=None):
        w = 0.5
        phip = 0.5
        phig = 0.5
        ptol = 1e-4

        self.data = []

        for idx in range(n_iter):
            rp = np.random.random(self.particles.shape)
            rg = np.random.random(self.particles.shape)
            
            self.pvel = w*self.pvel + phip*rp*(self.pbest - self.particles) + phig*rg*(self.global_best - self.particles)
            
            self.new_positions = np.minimum(np.maximum(self.particles + self.pvel, self.lb), self.ub)
            
            # To reduce function evaluations, we might choose to only evaluate when the new position is sufficiently
            # different from the previous position.
            self.to_evaluate = np.all(np.abs(self.new_positions - self.particles) > ptol, axis=1)
            self.particles = self.new_positions
            
            # Objective function is probably not Numpy vectorizable, and will be called using ordinary for loops.
            for i, to_eval in enumerate(self.to_evaluate):
              if to_eval:
                self.scores[i] = self.objfunc(self.particles[i])
                
                if self.scores[i] < self.pbest_score[i]:
                    self.pbest[i] = self.particles[i].copy()
                    self.pbest_score[i] = self.scores[i]

                    if self.scores[i] < self.global_best_score:
                        self.global_best = self.particles[i].copy()
                        self.global_best_score = self.scores[i]

            if keep_data:
              self.data.append(self.particles.copy())
            if verbose:
              print("Current Iteration:", idx, "with best score of", self.global_best_score, "at", self.global_best)
            
            # Callback function is passed the current iteration index, the current particle positions, and current particle scores
            # TO-DO: add docstrings
            if callback is not None:
                callback(idx, self.particles.copy(), self.scores.copy())

        return self.global_best_score

