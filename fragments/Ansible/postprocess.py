from bs4 import BeautifulSoup, Tag
import os

def main():
    for file in os.scandir('outgoing'):
        if ';' in file.name:
            prettify(file)
        else:
            os.remove(file)
        
def prettify(f):
            stream = open(f, 'r')
            soup = BeautifulSoup(stream, features='xml')
            stream.close()

            root = soup.find('properties-fragment')
            root = strip(root)

            with open(f, 'w') as stream:
                stream.write(soup.prettify())

def strip(element):
    s = BeautifulSoup('', features='xml')
    if type(element) == Tag:
        for node in element.contents:
            if type(node) == Tag:
                if node.contents:
                    node = strip(node)
                s.append(node)
        element.string = ''
        element.append(s)
        return element

if __name__ == '__main__':
    main()
