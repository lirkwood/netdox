import csv

def read():
    global kube
    kube = []
    global other
    other = []
    with open('../sources/domains.csv', 'r') as stream:
        for row in csv.reader(stream):
            if row[0] == 'Kubernetes':
                kube.append(row[1])
            else:
                other.append(row[1])

def compare():
    for i in kube:
        if i not in other:
            print(i)

def main():
    read()
    compare()

if __name__ == '__main__':
    main()
