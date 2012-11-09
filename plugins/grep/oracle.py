'''
oracle.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import core.data.kb.knowledge_base as kb
import core.data.kb.info as info

from core.controllers.plugins.grep_plugin import GrepPlugin
from core.data.bloomfilter.scalable_bloom import ScalableBloomFilter


class oracle(GrepPlugin):
    '''
    Find Oracle applications.
      
    @author: Andres Riancho (andres.riancho@gmail.com)
    '''

    def __init__(self):
        GrepPlugin.__init__(self)
        self._already_analyzed = ScalableBloomFilter()
        
    def grep(self, request, response):
        '''
        Plugin entry point. Grep for oracle applications.
        
        @param request: The HTTP request object.
        @param response: The HTTP response object
        @return: None
        '''
        url = response.getURL()
        if response.is_text_or_html() and url not in self._already_analyzed:
            self._already_analyzed.add(url)

            for msg in self._get_descriptiveMessages():
                # Remember that HTTPResponse objects have a faster "__in__" than
                # the one in strings; so string in response.getBody() is slower than
                # string in response
                if msg in response:
                    
                    i = info.info()
                    i.setPluginName(self.get_name())
                    i.set_name('Oracle application')
                    i.setURL(url)
                    i.set_id( response.id )
                    i.addToHighlight( msg )
                    msg = 'The URL: "' + url + '" was created using Oracle'
                    msg += ' Application server.'
                    i.set_desc( msg )
                    kb.kb.append( self , 'oracle' , i )

    def _get_descriptiveMessages( self ):
        res = []
        res.append('<!-- Created by Oracle ')
        return res
        
    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.print_uniq( kb.kb.get( 'oracle', 'oracle' ), 'URL' )

    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin greps every page for oracle messages, versions, etc.
        '''
