import os

import preprocess
import postprocess

def main():
    preprocess.main()
    print('Pre-process complete')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:convert.xsl -s:../../Sources/Ansible/report_json.xml -o:../../Sources/Ansible/report.xml')
    print('JSON converted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:main.xsl -s:../../Sources/Ansible/report.xml')
    print('Information extracted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:restructure.xsl -s:raw -o:outgoing')
    print('Restructure complete')
    postprocess.main()
    print('Post-process complete')

if __name__ == '__main__':
    main()
