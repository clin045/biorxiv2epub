import xml.etree.ElementTree as ET
import requests
import os
import re

def get_content_url(url):
    url = "https://www.biorxiv.org/content/10.1101/2021.12.22.473901v1"
    r = requests.get(url)
    thumburl = re.search(r'\"article\_thumbnail\"\ content=\"(.*?)\"',r.text).groups(1)[0]
    content_url = "/".join(thumburl.split("/")[:-1])
    return content_url

def resolve_xref(node):
    rid = node.attrib['rid']
    return f'[{rid}][{rid}]'


def resolve_formula(node):
    fname = node[0][0].attrib['{http://schema.highwire.org/Journal}id']
    resp = requests.get(content_url + "/" + fname + ".gif")
    os.makedirs("img",exist_ok=True)
    savepath = "img/" + fname + ".gif"
    with open(savepath,"wb+") as f:
        f.write(resp.content)
    if node.tag == "disp-formula":
        link_string = f'\n![]({savepath})\n'
    else:
        link_string = f'![]({savepath})'

    return link_string

def parse_fig(node):
    label = list(node.iter("label"))[0].text
    cap = list(node.iter("caption"))[0]
    title = list(cap.iter("title"))[0].text
    cap_text = parse_par(list(cap.iter("p"))[0])
    graphic_id = node.attrib['{http://schema.highwire.org/Journal}id']
    fname = graphic_id
    os.makedirs("img",exist_ok=True)
    resp = requests.get(content_url[:-6] + "/" + fname + ".large.jpg")
    savepath = "img/" + fname + ".jpg"
    with open(savepath,"wb+") as f:
        f.write(resp.content)
    fullcap = f'**{label} {title}** {cap_text}'
    link_string = f'\n![{fullcap}]({savepath})\n'
    return link_string

def sanitize(text):
    if text is None:
        return ""
    text = text.replace("[","\[")
    text = text.replace("]","\]")
    return text

def parse_par(node):
    partext = [sanitize(node.text)]
    for c in node:
        if(c.tag == "xref"):
            partext.append(resolve_xref(c))
        elif(c.tag == "italic"):
            partext.append(f'*{c.text}*')
        elif(c.tag == "bold"):
            partext.append(f'**{c.text}**')
        elif(c.tag == "sup"):
            partext.append(f'<sup>{c.text}</sup>')
        elif(c.tag == "sub"):
            partext.append(f'<sub>{c.text}</sub>')
        elif(c.tag == "inline-formula" or c.tag == "disp-formula"):
            partext.append(resolve_formula(c))
        else:
            print(c.tag)
        partext.append(sanitize(c.tail))
    return "".join(partext)

def parse_title(node):
    title_text = [sanitize(node.text)]
    for c in node:
        if(c.tag == "italic"):
            title_text.append(f'*{c.text}*')
        elif(c.tag == "bold"):
            title_text.append(f'**{c.text}**')
        elif(c.tag == "sup"):
            partext.append(f'<sup>{c.text}</sup>')
        elif(c.tag == "sub"):
            partext.append(f'<sub>{c.text}</sub>')
        title_text.append(c.tail)
    return "".join(title_text)

def parse_sec(sec,depth):
    sectext = []
    for c in sec:
        if c.tag == "title":
            sectext.append("#"*depth + " " + parse_title(c))
        if c.tag == "p":
            sectext.append(parse_par(c))
        if c.tag == "sec":
            sectext += parse_sec(c, depth+1)
        if c.tag == "fig":
            sectext.append(parse_fig(c))
            
    return sectext

def parse_meta(front):
    authors = []
    title = front[1][8][0].text
    for c in front[1][10]:
        if(c.tag == "contrib"):
            authors.append(c[0].attrib['{http://schema.highwire.org/Journal}sortable'])
    year = list(front[1].iter("history"))[0][2][2].text
    authstring = ", ".join(authors)
    titleblock = f"""
---
title: {title}
author: {authstring}
date: {year}
---
    """
    return titleblock

mdtext = []
tree = ET.parse("2021.12.22.473901.source.xml")
root = tree.getroot()
front, body, back = root
global content_url
content_url = get_content_url("test")

Parse the metadata
mdtext.append(parse_meta(front))
# Parse abstract
mdtext += parse_sec(front[1][27], 1)
# Parse body
for sec in body:
    mdtext += parse_sec(sec,1)

with open("converted.md","w+") as f:
    f.write("\n\n".join(mdtext))