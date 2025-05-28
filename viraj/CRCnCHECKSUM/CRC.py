def xor(a, b):
    result = ""
    for i in range(1, len(b)):
        result += '0' if a[i] == b[i] else '1'
    return result

def CRC(data, poly):
    len_poly = len(poly)
    divident = data + "0"*(len_poly - 1)
    
    div = divident[0:len_poly]

    for i in range(len_poly, len(divident)+1):
        print("Div: " + div)
        if div[0] == '1': # the div is of sufficient length for xor with poly
            div = xor(div, poly)
        else: # the div is not suff, drop dow next bit / xor with all 0
            div = xor(div, '0'*len_poly)
        if i < len(divident):
            div += divident[i]
    return div


data = input("\nEnter binary data: ").strip()
poly = input("Enter generator polynomial (in binary): ").strip()
crc = CRC(data, poly)
print("CRC = ",crc)
print("Transmited Data(with CRC): ",data+crc )