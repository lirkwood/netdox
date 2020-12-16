import os
import push
import editnote


def main():
    path = 'ReverseDNS/outgoing'
    section = 'reversedns'
    script = 'ptr_info.py'
    for file in os.scandir(path):
        filepath = path + '/' + os.path.basename(file)
        push.push(script, filepath, section)


if __name__ == '__main__':
    main()
