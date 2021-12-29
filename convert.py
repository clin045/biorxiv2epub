from xml.etree.ElementTree import fromstring, ElementTree
import requests
import os
import re
import argparse
import subprocess

def get_content_url(url):
    r = requests.get(url)
    suffix = re.search(r'data-apath=\"(.*?)\"',r.text).groups(1)[0]
    suffix_clean = ".".join(suffix.split(".")[:-1])
    content_url = "https://www.biorxiv.org/content" + suffix_clean
    return content_url



def resolve_xref(node):
    rid = node.attrib['rid']
    return f'[{rid}][{rid}]'


def resolve_formula(node):
    fname = node[0][0].attrib['{http://schema.highwire.org/Journal}id']
    resp = requests.get(content_url + "/embed/" + fname + ".gif")
    savepath = f"{article_id}_img/" + fname + ".gif"
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
    if len(list(cap.iter("title"))) > 0:
        title = list(cap.iter("title"))[0].text
    else:
        title = ""
    cap_text = parse_par(list(cap.iter("p"))[0])
    graphic_id = node.attrib['{http://schema.highwire.org/Journal}id']
    fname = graphic_id
    resp = requests.get(content_url + "/" + fname + ".large.jpg")
    savepath = f"{article_id}_img/" + fname + ".jpg"
    with open(savepath,"wb+") as f:
        f.write(resp.content)
    fullcap = f'**{label} {title}** {cap_text}'
    link_string = f'\n![{fullcap}]({savepath})\n'
    return link_string

def parse_list(node):
    list_string = "\n"
    for c in node:
        list_string += ("- " + "\n".join(parse_sec(c,1)) + "\n")
    return list_string

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
        elif(c.tag == "ext-link"):
            partext.append(c.text)
        elif(c.tag == "list"):
            partext.append(parse_list(c))
        else:
            print("Unknown tag:" + c.tag)
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
            name_node = list(c.iter("name"))[0]
            authors.append(name_node.attrib['{http://schema.highwire.org/Journal}sortable'])
    year = list(front[1].iter("history"))[0][2][2].text
    authstring = ", ".join(authors)
    titleblock = f"""
---
title: "{title}"
author: {authstring}
date: {year}
---
    """
    return titleblock

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="biorxiv article URL")
    args = parser.parse_args()

    global article_id
    article_id = "".join(args.url.split("/")[-1].split("."))
    os.makedirs(f"{article_id}_img",exist_ok=True)

    global content_url
    content_url = get_content_url(args.url)
    xml_url = content_url + ".source.xml"
    print(xml_url)
    xml = requests.get(xml_url).content
   
    tree = ElementTree((fromstring(xml)))
    front, body, back = tree.getroot()

    # Parse the metadata
    mdtext = []
    mdtext.append(parse_meta(front))
    # Parse abstract
    mdtext += parse_sec(front[1][27], 1)
    # Parse body
    for sec in body:
        mdtext += parse_sec(sec,1)

    with open(f'{article_id}.md',"w+") as f:
        f.write("\n\n".join(mdtext))
    cmd = ["pandoc", f"{article_id}.md","-o", f"{article_id}.epub"]
    subprocess.Popen(cmd)

