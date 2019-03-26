import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation


df = pd.read_csv("actual_1.csv")

df_grid = pd.read_csv("grid_data.csv")

df_grid["cost"] = df_grid["cost"].apply(lambda x: 5 if x==1e9 else x)
grid_size = (20, 20)

n_vars = 8

data = df.values.reshape(df.shape[0], df.shape[1]//(n_vars + 1), n_vars + 1)

y_data = data[:, :, 1]
x_data = data[:, :, 0]

def show_animation(title="", df_grid=None):
    fig, ax = plt.subplots()

    if df_grid is not None:
        gx, gy = grid_size
        ax.contourf(df_grid["X"].values.reshape(gx, gy), df_grid["Y"].values.reshape(gx, gy), df_grid["cost"].values.reshape(gx, gy), levels=100, cmap=plt.cm.YlGnBu_r)

    p, = ax.plot([], [], marker='o', linestyle="None", color="orange")
    
    plt.xlim(x_data.min(), x_data.max())
    plt.ylim(y_data.min(), y_data.max())
    plt.xlabel("Column Pressure, kPa")
    plt.ylabel("Number of Stages")
    plt.title(title)

    def animate(i):
        p.set_data(x_data[i], y_data[i])
        return p,

    anim = animation.FuncAnimation(fig, animate, frames=x_data.shape[0]) #, blit=True)
    plt.show()


def plot_iterations(n=4, figsize=(4,3), max_num_per_row=4, df_grid=None):
    data_idx = list(np.linspace(0, x_data.shape[0] - 1, n, endpoint=True, dtype=np.int32))
    n_rows = math.ceil(n / max_num_per_row)
    n_cols = min(n, max_num_per_row)
    fig_width = figsize[0] * n_cols
    fig_height = figsize[1] * n_rows

    plt.figure(figsize=(fig_width, fig_height))
    for i in range(n):
        plt.subplot(n_rows, n_cols, i + 1)

        if df_grid is not None:
            gx, gy = grid_size
            plt.contourf(df_grid["X"].values.reshape(gx, gy), df_grid["Y"].values.reshape(gx, gy), df_grid["cost"].values.reshape(gx, gy), levels=100, cmap=plt.cm.YlGnBu_r)

        plt.xlim(x_data.min(), x_data.max())
        plt.ylim(y_data.min(), y_data.max())
        plt.plot(x_data[data_idx[i]], y_data[data_idx[i]], color="orange", marker='.', linestyle="None")
        plt.title("Iteration {}".format(data_idx[i] + 1))
        plt.ylabel("Column Pressure, kPa")
        plt.xlabel("Number of Stages")

    plt.tight_layout()
    plt.show()


def plot_cost_graph(figsize=(4,3)):
    plt.figure(figsize=figsize)

    costs = data[:, :, -1].min(axis=1)

    plt.plot(np.arange(costs.size), costs, 'r')
    plt.ylabel("TAC ($ million/year)")
    plt.xlabel("Iteration No.")
    plt.show()




# show_animation(df_grid=df_grid)
plot_iterations(n=4, df_grid=df_grid)
# plot_cost_graph()
