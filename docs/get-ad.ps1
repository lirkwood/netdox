$list = "ad.allette.com.au",
"200.168.192.in-addr.arpa",
"13.168.192.in-addr.arpa",
"12.168.192.in-addr.arpa",
"6.168.192.in-addr.arpa",
"7.168.192.in-addr.arpa",
"8.168.192.in-addr.arpa",
"14.168.192.in-addr.arpa",
"20.168.192.in-addr.arpa",
"21.168.192.in-addr.arpa",
"allette.com.au",
"docker.internal",
"download.pageseeder.com",
"hg.pageseeder.com",
"ivy.pageseeder.com",
"lixi.org.au.internal",
"natspec.com.au.internal",
"natspec.org.internal",
"nonzero.com.au",
"oxforddigital.com.au.internal",
"pageseeder.com.internal",
"pageseeder.net.internal",
"pageseeder.org.internal",
"pbs.gov.au.internal",
"ps-test.pageseeder.com",
"remotephcmanuals.com.au.internal",
"stratabox.com.au.internal",
"SY4",
"tekreader.com.internal"


foreach ($zone in $list) {
    Get-DnsServerResourceRecord -ZoneName $zone -ComputerName "ad.allette.com.au" | ConvertTo-Json -Depth 10 | Out-File -width 300 -FilePath "c:\Users\lkirkwood\network-documentation\Sources\records\$zone.json"
}