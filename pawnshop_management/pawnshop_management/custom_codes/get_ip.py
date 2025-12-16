from operator import gt
from requests import get
import frappe

@frappe.whitelist()
def get_ip():
    # ip = get('https://api.ipify.org').text
    # print(f'My public IP address is: {ip}')
    ip = frappe.local.request_ip
    return ip

@frappe.whitelist()
def get_ip_from_settings():
    cavite_city = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - CC")
    poblacion = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - POB")
    molino = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - MOL")
    gtc = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - GTC")
    tanza = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - TNZ")
    alapan = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - BUC")
    noveleta = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - NOV")
    pascam = frappe.get_doc('Branch IP Addressing', "Garcia's Pawnshop - PSC")
    test = frappe.get_doc('Branch IP Addressing', "TEST")

    return {
        "cavite_city" : cavite_city.ip_address, 
        "poblacion": poblacion.ip_address,
        "molino": molino.ip_address,
        "gtc": gtc.ip_address,
        "tanza": tanza.ip_address,
        "alapan": alapan.ip_address,
        "noveleta": noveleta.ip_address,
        "pascam": pascam.ip_address,
        "test": test.ip_address
        }
