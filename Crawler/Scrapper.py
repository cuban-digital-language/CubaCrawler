from bs4 import BeautifulSoup
from urllib3.exceptions import LocationParseError
try:
    from .ScrapBase import ScrapBase, UnreachebleURL, ProxyConfigError
except (ModuleNotFoundError,ImportError):
    from ScrapBase import ScrapBase, UnreachebleURL, ProxyConfigError
import requests
import re
import logging
logger = logging.getLogger('scrapper')

from bs4 import BeautifulSoup
try:
    from .ScrapBase import ScrapBase
except (ModuleNotFoundError, ImportError):
    from ScrapBase import ScrapBase
import requests
import re
import logging
from datetime import datetime

logger = logging.getLogger('scrapper')
logging.basicConfig(level=logging.DEBUG)

sps = re.compile('  +')
comm = re.compile('comment')
#attach = re.compile("^attachment")
#authorsplit = re.compile('[Pp]or *?\:')

class CubaDebate(ScrapBase):

    def __init__(self,url,proxy=None):
        super().__init__(url,proxy)
        self.__html_text = None

    def _request_html(self, url, proxy):
        #logger.debug('_request_html {}, {}'.format(type(url), type(proxy)))
        try:
            response = requests.get(url, proxies=proxy)
        except Exception as e:
            if isinstance(e, LocationParseError):
                try:
                    response = requests.get(url, proxies=proxy['http'])
                except Exception as e:
                    if isinstance(e, LocationParseError):
                        logger.debug(e)
                        raise ProxyConfigError
                    logger.debug(e)
                    raise UnreachebleURL
            else:
                logger.debug(e)
                raise UnreachebleURL
        #logger.debug(response)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            raise Exception("received code = %d" % response.status_code)
        return response.text

    def _Scrap(self, url, proxy):
        """
        Search for div with class:note_content and delete footnotes in order to have
        only the desired new text
        """
        #logger.debug('_Scrap params {}, {}'.format(url,proxy))
        if self.__html_text is None:
            self.__html_text = self._request_html(url, proxy)
        #logger.debug(html_text)

        soup = BeautifulSoup(self.__html_text, 'lxml')
        img = None
        imgb = True
        ans = soup.find("div", {"class": "note_content"})
        img = ans.find("img")
        if img:
            img = img['src']
        ans = ans.text.strip().replace('\n',' ')
        por = soup.find("span",{"class":"extraauthor"})
        if por:
            por = por.get_text()
        title = soup.find('h2',{"class": "title"}).text
        return {'text':ans,'title':title,'img':img, 'author':por}

    def _Comment(self, url, proxy):
        return self._extract_comments(url, proxy)

    def _extract_comments(self, url: str, proxy):
        """
        Retorna una lista de diccionarios que contienen el texto
        de los comentarios y la fecha en que se hicieron.
        """
        if self.__html_text is None:
            self.__html_text = self._request_html(url, proxy)
        soup = BeautifulSoup(self.__html_text, 'lxml')

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
                    temp = temp.replace('\n',' ')
                    temp = sps.sub(' ',temp)
                    tt['text'] = temp
                elif j.name == 'div' and j['class'] == 'commentmetadata':
                    tt['date'] = self._convert_to_datetime(j.get_text().strip())
            comments.append(tt)

        new_request = comments_section.find(
            'a', attrs={'class': 'pscroll_next'})
        while new_request != None:  # comprobar obtener mas comentarios
            new_url = new_request.get('data-href')
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
                        temp = temp.replace('\n',' ')
                        temp = sps.sub(' ',temp)
                        tt['text'] = temp
                    elif j.name == 'div' and j['class'] == 'commentmetadata':
                        tt['date'] = self._convert_to_datetime(j.get_text().strip())
                comments.append(tt)
            new_request = new_soup.find(
                'a', attrs={'class': 'pscroll_next'})

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
        return 'cubadebate' in url.lower()
