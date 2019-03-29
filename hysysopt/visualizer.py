import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def visualizer():
    return Visualizer()

class Visualizer:
    def __init__(self):
        self.data = None
        self.grid_data = None

        # Visualizer parameters
        self.x_index = 0
        self.y_index = 1
        self.xlabel = "x"
        self.ylabel = "y"
    
    def load(self, filename, n_vars):
        self.data = pd.read_csv("actual_1.csv")

    def load_grid(self, grid_filename, grid_size):
        self.grid_data = pd.read_csv("grid_data.csv")

        self.grid_size = grid_size

    def view(self, n=4, figsize=(4,3), max_num_per_row=4):
        if self.data is None:
            raise FileNotFoundError("No data has been loaded yet.")
        
        data = self.data.values.reshape(df.shape[0], df.shape[1]//(n_vars + 1), n_vars + 1)

        y_data = data[:, :, self.x_index]
        x_data = data[:, :, self.y_index]

        data_idx = list(np.linspace(0, x_data.shape[0] - 1, n, endpoint=True, dtype=np.int32))
        n_rows = math.ceil(n / max_num_per_row)
        n_cols = min(n, max_num_per_row)
        fig_width = figsize[0] * n_cols
        fig_height = figsize[1] * n_rows

        plt.figure(figsize=(fig_width, fig_height))
        for i in range(n):
            plt.subplot(n_rows, n_cols, i + 1)

            if self.grid_data is not None:
                gx, gy = self.grid_size
                plt.contourf(self.grid_data["X"].values.reshape(gx, gy),
                             self.grid_data["Y"].values.reshape(gx, gy),
                             self.grid_data["cost"].values.reshape(gx, gy),
                             levels=100,
                             cmap=plt.cm.YlGnBu_r)

            plt.xlim(x_data.min(), x_data.max())
            plt.ylim(y_data.min(), y_data.max())
            plt.plot(x_data[data_idx[i]], y_data[data_idx[i]], color="orange", marker='.', linestyle="None")
            plt.title("Iteration {}".format(data_idx[i] + 1))
            plt.ylabel(self.xlabel)
            plt.xlabel(self.ylabel)

        plt.tight_layout()
        plt.show()
    
    def view_cost_graph(self):
        if self.data is None:
            raise FileNotFoundError("No data has been loaded yet.")
        
        plt.figure(figsize=figsize)

        costs = self.data[:, :, -1].min(axis=1)

        plt.plot(np.arange(costs.size), costs, 'r')
        plt.ylabel("TAC ($ million/year)")
        plt.xlabel("Iteration No.")
        plt.show()

    

    def view_animation(self, title=""):
        if self.data is None:
            raise FileNotFoundError("No data has been loaded yet.")
        
        y_data = data[:, :, self.x_index]
        x_data = data[:, :, self.y_index]

        fig, ax = plt.subplots()

        if self.grid_data is not None:
            gx, gy = self.grid_size
            plt.contourf(self.grid_data["X"].values.reshape(gx, gy),
                        self.grid_data["Y"].values.reshape(gx, gy),
                        self.grid_data["cost"].values.reshape(gx, gy),
                        levels=100,
                        cmap=plt.cm.YlGnBu_r)
        
        p, = ax.plot([], [], marker='o', linestyle="None", color="orange")
        
        plt.xlim(x_data.min(), x_data.max())
        plt.ylim(y_data.min(), y_data.max())
        plt.ylabel(self.xlabel)
        plt.xlabel(self.ylabel)
        plt.title(title)

        def animate(i):
            p.set_data(x_data[i], y_data[i])
            return p,

        anim = animation.FuncAnimation(fig, animate, frames=x_data.shape[0]) #, blit=True)
        plt.show()

