import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import random
from sklearn.decomposition import PCA
from shapely.geometry import Polygon
%matplotlib tk

plt.close('all')


if __name__ == '__main__':
    
    random.seed(10)
    
    # variables' name
    joints_list = ['joint_i', 'joint_j']
    vel_list = ['vel_i', 'vel_j']
    phase_list = ['phase_i', 'phase_j']
    color_list=['b', 'r']
    
    #%% Sample data generation

    #create the normalized timeline as an array from 0 to 100
    dt = 1
    n = 100
    samples = np.linspace(0, dt, int(n*dt)).transpose()
    
    noise = 0.8
 
    #create dataset A made of 10 repetition
    dataset_A = []
    plt.figure()
    for i in np.arange(10):
        data_A = pd.DataFrame(np.array([samples,
                                        np.sin(samples*(6+random.uniform(-noise, noise)))+ np.random.default_rng().uniform(-noise, noise),
                                        np.sin(samples*(1+random.uniform(-noise, noise)))+ np.random.default_rng().uniform(-noise, noise)-2.5]).transpose(), 
                              columns=['time'] + joints_list)
        plt.plot(data_A[['joint_i', 'joint_j']])
        dataset_A.append(data_A)
    plt.title('Dataset B')
    plt.xlabel('Normalized time')
    plt.ylabel('Joint position (rad)')

    #create dataset B made of 10 repetition
    dataset_B = []
    plt.figure()
    for i in np.arange(10):
        data_B = pd.DataFrame(np.array([samples,
                                        np.sin(samples*(4+random.uniform(-noise, noise)))+ np.random.default_rng().uniform(-noise, noise, 1),
                                        np.sin(samples*(3+random.uniform(-noise, noise)))+ np.random.default_rng().uniform(-noise, noise, 1)-2.5]).transpose(), 
                              columns=['time'] + joints_list)
        plt.plot(data_B[['joint_i', 'joint_j']])
        dataset_B.append(data_B)
    plt.title('Dataset B')
    plt.xlabel('Normalized time')
    plt.ylabel('Joint position (rad)')
        
    # Plot both datasets with mean and standard deviation
    fig, ax = plt.subplots(2)
    for i, c in enumerate(joints_list):
                 data_mean_A = pd.concat(dataset_A, axis=1)[c].mean(axis=1)
                 data_std_A = pd.concat(dataset_A, axis=1)[c].std(axis=1)
                 ax[0].plot(data_mean_A, c=color_list[i], label=joints_list[i])
                 ax[0].fill_between(data_mean_A.index, data_mean_A-data_std_A, data_mean_A+data_std_A, color=color_list[i], alpha=0.2)
                 ax[0].set_title('Dataset A')
                 
                 data_mean_B = pd.concat(dataset_B, axis=1)[c].mean(axis=1)
                 data_std_B = pd.concat(dataset_B, axis=1)[c].std(axis=1)
                 ax[1].plot(data_mean_B, c=color_list[i], label=joints_list[i])
                 ax[1].fill_between(data_mean_B.index, data_mean_B-data_std_B, data_mean_B+data_std_B, color=color_list[i], alpha=0.2)
    ax[0].set_title('Dataset A')    
    ax[0].set_ylabel('Joint position (rad)')
    ax[0].legend()
    ax[1].set_title('Dataset B')
    ax[1].set_xlabel('Normalized time')
    ax[1].set_ylabel('Joint position (rad)')
    ax[1].legend()
    
    #%% Run PCA
    
    #center dataset A
    dataset_A_centered = pd.concat(dataset_A)[joints_list] - pd.concat(dataset_A)[joints_list].mean()
    # Run PCA on the first data set
    pca_A = PCA(n_components=2)
    pca_data = pca_A.fit(dataset_A_centered)
    
    pca_A_frame = pca_A.components_
    pca_A_variance_ratio = pca_A.explained_variance_ratio_
    
    # Project dataset B in PCA_A
    dataset_B_centered = pd.concat(dataset_B)[joints_list] - pd.concat(dataset_B)[joints_list].mean()
    dataset_B_projected = np.matmul(dataset_B_centered.to_numpy(), pca_A_frame.transpose())
    
    # Run PCA on the reprojected data
    pca_B = PCA(n_components=2)
    pca_data = pca_B.fit(dataset_B_projected)
    
    pca_B_frame = pca_B.components_
    pca_B_variance_ratio = pca_B.explained_variance_ratio_
    
    # Get The weight of B variable in the world frame
    result_B = abs(np.matmul(pca_B_frame, pca_A_frame))

    # Compute subtraction
    sub = result_B-abs(pca_A_frame)
    
    # Plot results
    fig = plt.figure(figsize=(8,10))
    
    ax = fig.add_subplot(4, 2,1)
    ax.bar(joints_list, abs(pca_A_frame[0,:]), color=color_list)
    ax.set_title("PC 1 = %.2f" % pca_A_variance_ratio[0])
    ax.set_ylabel('Dataset A')
    ax.set_ylim([-0.1, 1])

    ax = fig.add_subplot(4,2,2)
    ax.bar(joints_list, abs(pca_A_frame[1,:]), color=color_list)
    ax.set_title("PC 2 = %.2f" % pca_A_variance_ratio[1])
    ax.set_ylim([-0.1, 1])

    ax = fig.add_subplot(4, 2,3)
    ax.bar(joints_list, abs(result_B[0,:]), color = color_list)
    ax.set_ylabel('Dataset B')
    ax.set_ylim([-0.1, 1])

    ax = fig.add_subplot(4,2,4)
    ax.bar(joints_list, abs(result_B[1,:]), color=color_list)
    ax.set_ylim([-0.1, 1])

    ax = fig.add_subplot(4,2,5)
    ax.bar(joints_list, sub[0,:], color='orange')
    ax.set_ylabel('Dataset B - Dataset A')
    ax.set_ylim([-0.5, 0.5])


    ax = fig.add_subplot(4,2,6)
    ax.bar(joints_list, sub[1,:], color='orange')
    ax.set_ylim([-0.5, 0.5])

    ax = fig.add_subplot(4,1,4)
    res_prop = np.array([sub[0, :] * pca_A_variance_ratio[0], sub[1, :] * pca_A_variance_ratio[1]]).flatten()
    ax.bar(np.arange(4), res_prop, color='orange')
    ax.set_ylim([-0.5, 0.5])
    ax.set_title('Dataset B - Dataset A reported to the explained variance ratio')
    fig.tight_layout()
    
    #%% Run CRP
    
    # Plot results
    fig = plt.figure(figsize=(14,6))
    ax0= fig.add_subplot(2, 5, 1)
    ax1= fig.add_subplot(2, 5, 6)
    ax2= fig.add_subplot(2, 5, 2)
    ax3= fig.add_subplot(2, 5, 7)
    ax4= fig.add_subplot(2, 5, 3)
    ax5= fig.add_subplot(2, 5, 8)
    ax6= fig.add_subplot(2, 5, 4)
    ax7= fig.add_subplot(2, 5, 9)
    ax8= fig.add_subplot(1, 5, 5)

    for dA, dB in zip(dataset_A, dataset_B):
        for i, c in enumerate(joints_list):
            
            #Compute velocity
            dA[vel_list[i]]=dA[c].diff()/dA['time'].diff()
            dB[vel_list[i]]=dB[c].diff()/dB['time'].diff()

            # Range normalization position and velocity dataset A
            dA[c] = 2*((dA[c]-dA[c].min()) /
                           (dA[c].max()-dA[c].min()))-1
            dA[vel_list[i]] = 2*((dA[vel_list[i]]-dA[vel_list[i]].min()) /
                           (dA[vel_list[i]].max()-dA[vel_list[i]].min()))-1
            
            
            # Plot position and velocity for dataset A
            ax0.plot(dA[c],  c=color_list[i])
            ax0.set_title('Position')
            ax0.set_ylabel('Joint Position')
            ax0.set_ylabel('Dataset A')
            
            ax2.plot(dA[vel_list[i]],  c=color_list[i])
            ax2.set_title('Velocity')
            ax2.set_ylabel('Joint angular velocity')
            
            
            # Range normalization position and velocity for dataset B
            dB[c] = 2*((dB[c]-dB[c].min()) /
                           (dB[c].max()-dB[c].min()))-1
            dB[vel_list[i]] = 2*((dB[vel_list[i]]-dB[vel_list[i]].min()) /
                           (dB[vel_list[i]].max()-dB[vel_list[i]].min()))-1
            
            # Plot poisiton and velocity for dataset B
            ax1.plot(dB[c], c=color_list[i])
            ax1.set_ylabel('Dataset B')
            ax1.set_ylabel('Joint Position')
            ax1.set_xlabel('time')

            ax3.plot(dB[vel_list[i]], c=color_list[i])
            ax3.set_xlabel('time')
            ax3.set_ylabel('Joint angular velocity')

            # Plot position with velocity for dataset A
            ax4.plot(dA[c], dA[vel_list[i]], c=color_list[i])
            ax4.set_title('Position/Velocity')
            ax4.set_ylabel('Joint angular velocity')
            
            # Plot position and velocity for dataset B
            ax5.plot(dB[c], dB[vel_list[i]], c=color_list[i])
            ax5.set_ylabel('Joint angular velocity')
            ax5.set_xlabel('Joint position')

            # Extract Phase Angle
            dA[phase_list[i]] = np.arctan(dA[vel_list[i]], dA[c])
            dB[phase_list[i]] = np.arctan(dB[vel_list[i]], dB[c])
        
            ax6.plot(dA[phase_list[i]],  c=color_list[i])
            ax6.set_title('Phase angle')
            ax6.set_ylabel('Phase angle (rad)')
            
            ax7.plot(dB[phase_list[i]],  c=color_list[i])
            ax7.set_xlabel('time')
            ax7.set_ylabel('Phase angle (rad)')
            ax7.set_xlabel('Time')

        
        # Compute CRP
        dA['CRP_ij']= dA[phase_list[1]]-dA[phase_list[0]]
        dB['CRP_ij']= dB[phase_list[1]]-dB[phase_list[0]]
        
    
    # Compute mean and standard CRP profile for dataset A
    data_mean_A = pd.concat(dataset_A, axis=1)['CRP_ij'].mean(axis=1)
    data_std_A = pd.concat(dataset_A, axis=1)['CRP_ij'].std(axis=1)
    ax8.plot(data_mean_A, c='orange', label='Dataset A')
    ax8.fill_between(data_mean_A.index, data_mean_A-data_std_A, data_mean_A+data_std_A, color='orange', alpha=0.25)
                 
    # Compute mean and standard CRP profile for dataset B
    data_mean_B = pd.concat(dataset_B, axis=1)['CRP_ij'].mean(axis=1)
    data_std_B = pd.concat(dataset_B, axis=1)['CRP_ij'].std(axis=1)
    ax8.plot(data_mean_B, c='olive', label='Dataset B')
    ax8.legend()
    ax8.fill_between(data_mean_B.index, data_mean_B-data_std_B, data_mean_B+data_std_B, color='olive', alpha=0.25)
    
    # Compute the area between both curves
    polygon_points = []  # creates a empty list where we will append the points to create the polygon

    for x, y in zip(samples, data_mean_A.iloc[1:]):
        polygon_points.append((x*100, y))  # append all xy points for curve 1

    for x,y in zip(samples[::-1], data_mean_B.iloc[::-1][:-1]):
        polygon_points.append((x*100, y))  # append all xy points for curve 2 in the reverse order (from last point to first point)

    for x,y in zip([samples[0]], [data_mean_A.iloc[1]]):
        polygon_points.append((x*100,y))  # append the first point in curve 1 again, to it "closes" the polygon

    polygon = Polygon(polygon_points)
    area = polygon.area
    x,y = polygon.exterior.xy
    
    # Plot the area between the curves
    ax8.fill(x, y, alpha=0.5, c='pink')
    ax8.set_title('CRP Plot \n Area : %.2f' % area)
    plt.tight_layout()
    
    

    
    
