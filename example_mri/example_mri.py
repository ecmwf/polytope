import mat73

if __name__ == "__main__":
    data = mat73.loadmat("./data/data.mat")
    print(data)
