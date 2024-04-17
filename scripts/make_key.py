import csv

from agent0.core.base.make_key import make_private_key

private_key = make_private_key()

with open('private_keys.csv', 'w', newline='', encoding='UTF-8') as file:
    writer = csv.writer(file)
    writer.writerow(['Private Key'])
    writer.writerow([private_key])
