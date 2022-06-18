from datetime import datetime
from cgitb import text
from bs4 import BeautifulSoup
from urllib3.exceptions import LocationParseError
try:
    from .ScrapBase import ScrapBase, UnreachebleURL, ProxyConfigError
except (ModuleNotFoundError, ImportError):
    from ScrapBase import ScrapBase, UnreachebleURL, ProxyConfigError
import requests
import re
import logging
logger = logging.getLogger('scrapper')

try:
    from .ScrapBase import ScrapBase
except (ModuleNotFoundError, ImportError):
    from ScrapBase import ScrapBase

logger = logging.getLogger(__name__)

sps = re.compile('  +')
comm = re.compile('comment')


class CubaDebate(ScrapBase):
    HOME = 'page'
    MORE_READER = 'estadistica_ga'
    MORE_SHARED = 'estadistica_addthis'
    MORE_COMMENT = "estadistica_comments consumo_last_section"

    def __init__(self, url, proxy=None):
        super().__init__(url, proxy)
        self._html_text = None

    def _Source(self):
        return "CubaDebate"

    def _Scrap(self, url, proxy):
        """
        Search for div with class:note_content and delete footnotes in order to have
        only the desired new text
        """

        soup = BeautifulSoup(self._html_text, 'lxml')
        img = None
        ans = soup.find("div", {"class": "note_content"})
        img = ans.find("img")
        if img:
            img = img['src']
        imgfooter = None
        text = ''
        fuente = None
        for i in ans.find_all('p'):
            att = i.attrs.get('class')
            if att:
                for j in att:
                    if j == 'wp-caption-text':
                        imgfooter = i.text.strip()
                        break
            else:
                txt = i.text.strip()
                if re.search('Fuente:', txt, re.I):
                    fuente = txt.split(':')[1].strip()
                    continue
                text += txt+' '
        ans = text.strip()
        #ans = ans.text.strip().replace('\n',' ')
        por = soup.find("span", {"class": "extraauthor"})
        if por:
            por = por.get_text()
        title = soup.find('h2', {"class": "title"}).text
        date = soup.find('time')
        date = datetime.strptime(date.attrs['datetime'], '%Y-%m-%d %H:%M:%S')
        return {'text': ans, 'title': title, 'img': img, 'author': por, "pub_date": date,
                'img_footer': imgfooter, 'notice_source': fuente}

    def _Comment(self, url, proxy):
        return self._extract_comments(url, proxy)

    def _extract_comments(self, url: str, proxy):
        """
        Retorna una lista de diccionarios que contienen el texto
        de los comentarios y la fecha en que se hicieron.
        """
        soup = BeautifulSoup(self._html_text, 'lxml')

        # buscar la seccion de los comentarios
        comments_section = soup.find('section', id='comments')
        if comments_section is None:
            return []
        comments_section = comments_section.find('ul')
        if comments_section is None:
            return []

        comments = []
        proc_com = comments_section.find_all(
            'li', attrs={'id': comm})
        for i in proc_com:
            data = i.contents[0].contents[0]
            tt = {}
            for j in data.children:
                if j.name == 'cite':
                    tt['author'] = str(j.contents[0].get_text())
                elif j.name == 'p':
                    temp = str(j.get_text()).strip()
                    temp = temp.replace('\n', ' ')
                    temp = sps.sub(' ', temp)
                    tt['text'] = temp
                elif j.name == 'div' and 'commentmetadata' in j['class']:
                    tt['date'] = self._convert_to_datetime(
                        j.get_text().strip())
            comments.append(tt)

        new_request = soup.find(
            'a', attrs={'class': 'next'})
        while new_request != None:  # comprobar obtener mas comentarios
            new_url = new_request.get('href')
            new_html = self._request_html(new_url, proxy)
            new_soup = BeautifulSoup(new_html, 'lxml')
            proc_com = new_soup.find_all(
                'li', attrs={'id': comm})
            for i in proc_com:
                data = i.contents[0].contents[0]
                tt = {}
                for j in data.children:
                    if j.name == 'cite':
                        tt['author'] = str(j.contents[0].get_text())
                    elif j.name == 'p':
                        temp = str(j.get_text()).strip()
                        temp = temp.replace('\n', ' ')
                        temp = sps.sub(' ', temp)
                        tt['text'] = temp
                    elif j.name == 'div' and 'commentmetadata' in j['class']:
                        tt['date'] = self._convert_to_datetime(
                            j.get_text().strip())
                comments.append(tt)
            new_request = new_soup.find(
                'a', attrs={'class': 'next'})

        return comments

    def _convert_to_datetime(self, date_string):
        """
        Covierte un string con la estructura 'd m y a las h:m' a datetime
        """
        dict_month = {
            'enero': 'Jan',
            'febrero': 'Feb',
            'marzo': 'Mar',
            'abril': 'Apr',
            'mayo': 'May',
            'junio': 'Jun',
            'julio': 'Jul',
            'agosto': 'Aug',
            'septiembre': 'Sep',
            'octubre': 'Oct',
            'noviembre': 'Nov',
            'diciembre': 'Dec'}

        date = date_string.split()

        date.remove('a')
        date.remove('las')
        date[1] = dict_month[date[1]]
        string = "".join(date)

        return datetime.strptime(string, '%d%b%Y%H:%M')

    @staticmethod
    def can_crawl(url):
        return 'cubadebate.cu' in url.lower()

    @staticmethod
    def auto_crawl(pages=10, proxy=None, crawl_len=None, timeout=100, clean=False):
        links = []

        for i in range(400, pages + 1):
            with open(f'cubadebate_page_{i}.html', 'a+' if not clean else 'w+') as page:
                page.close()
            with open(f'cubadebate_page_{i}.html', 'r+') as page:
                html = page.read()
                if not any(html):
                    crawl = CubaDebate('', proxy)
                    try:
                        html = crawl._request_html(
                            f'http://www.cubadebate.cu/page/{i}', proxy, timeout)
                    except UnreachebleURL:
                        print('error in page', i)
                        continue
                    page.write(html)

                page.close()
                soup = BeautifulSoup(html, 'lxml')
                # soup = soup.find('section', {'id': 'page' if session is None else session})

                for link in soup.find_all('a'):
                    href = link.get('href')
                    if not href in links:
                        links.append(href)

                    if not crawl_len is None and len(link) >= crawl_len:
                        break
                else:
                    continue
                break

        def filter(url):
            return (
                type(url) == type('')
                and url.startswith('http://www.cubadebate.cu/noticias')
                and not '#respond' in url
                and not '#anexo' in url
            )

        return [CubaDebate(url, proxy) for url in links if filter(url)]

    def json_export(cuba_crawl_list, filter=lambda d, c: True, name_file="cubadebate", clean_text=lambda x: x):
        with open(f'{name_file}.json', 'w+') as txt:
            txt.write('[')
            for i, crawl in enumerate(cuba_crawl_list):
                try:
                    data = crawl.data
                    comment = crawl.comment
                except UnreachebleURL:
                    continue

                if filter(data, comment):
                    result = '{ \n'
                    result += f'"url": "{crawl._url}",\n'
                    result += f'"title": "{clean_text(data["title"])}",\n'
                    result += f'"text": "{clean_text(data["text"])}", \n'
                    result += f'"author": "{clean_text(data["author"])}",\n'
                    result += f'"date": "{data["pub_date"]}",\n'
                    result += f'"comments": [ '

                    try:
                        for c in comment:
                            result += '{\n'
                            result += f'"text": "{clean_text(c["text"])}",\n'
                            result += f'"author": "{clean_text(c["author"])}",\n'
                            result += f'"date": "{c["date"]}"\n'
                            result += '},'
                    except: pass
                    txt.write(result[0: -1] + ']},')
                print(i, '-->', crawl._url)
            txt.write(']')


if __name__ == '__main__':
    def clean_text(text):
        if text is None:
            return text
        return text.replace("\"", "\'").replace('\t', '').replace('\\', '').replace('\n', ' ')

    cuba_crawl_list = CubaDebate.auto_crawl(pages=600, timeout=1000000)
    CubaDebate.json_export(cuba_crawl_list, filter=lambda d,
                           c: True, clean_text=clean_text)
