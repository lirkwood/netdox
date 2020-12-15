import os
import ansible.preprocess
import ansible.postprocess


def main():
    ansible.preprocess.main()
    print('Pre-process complete')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:ansible/convert.xsl -s:../Sources/Ansible/report_json.xml -o:../Sources/Ansible/report.xml')
    print('JSON converted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:ansible/main.xsl -s:../Sources/Ansible/report.xml')
    print('Information extracted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:ansible/restructure.xsl -s:ansible/raw -o:ansible/outgoing')
    print('Restructure complete')
    ansible.postprocess.main()
    print('Post-process complete')

if __name__ == '__main__':
    main()
