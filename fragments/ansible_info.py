import os
import push
import editnote

def main():
    path = 'Ansible/outgoing'
    section = 'ansible'
    for file in os.scandir(path):
        filepath = path + '/' + os.path.basename(file)
        docid = os.path.basename(file).split(';')[0]
        fragment = os.path.basename(file).split(';')[1]
        push.push(filepath, section)
        self = os.path.basename(__file__)
        editnote.post(section, docid, fragment, self)

if __name__ == '__main__':
    main()