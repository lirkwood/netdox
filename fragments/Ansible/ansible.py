import os
import ansible.preprocess
import ansible.postprocess


def main():
    ansible.preprocess.main()
    print('Pre-process complete')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:C:/Users/linus/network-documentation/Fragments/ansible/convert.xsl -s:C:/Users/linus/network-documentation/Sources/Ansible/report_json.xml -o:C:/Users/linus/network-documentation/Sources/Ansible/report.xml')
    print('JSON converted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:C:/Users/linus/network-documentation/Fragments/ansible/main.xsl -s:C:/Users/linus/network-documentation/Sources/Ansible/report.xml')
    print('Information extracted')
    os.system('java -jar c:/saxon/saxon-he-10.3.jar -xsl:C:/Users/linus/network-documentation/Fragments/ansible/restructure.xsl -s:C:/Users/linus/network-documentation/Fragments/ansible/raw -o:C:/Users/linus/network-documentation/Fragments/ansible/outgoing')
    print('Restructure complete')
    ansible.postprocess.main()
    print('Post-process complete')

if __name__ == '__main__':
    main()
