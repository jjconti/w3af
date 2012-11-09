'''
eval.py

Copyright 2008 Viktor Gazdag & Andres Riancho

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
import re

import core.controllers.output_manager as om
import core.data.constants.severity as severity
import core.data.kb.knowledge_base as kb
import core.data.kb.vuln as vuln

from core.controllers.plugins.audit_plugin import AuditPlugin
from core.controllers.delay_detection.exact_delay import exact_delay
from core.controllers.delay_detection.delay import delay
from core.data.fuzzer.fuzzer import create_mutants
from core.data.fuzzer.utils import rand_alpha
from core.data.options.opt_factory import opt_factory
from core.data.options.option_list import OptionList


class eval(AuditPlugin):
    '''
    Find insecure eval() usage.

    @author: Viktor Gazdag ( woodspeed@gmail.com )
    @author: Andres Riancho (andres.riancho@gmail.com)
    '''
    
    PRINT_STRINGS = (
        # PHP http://php.net/eval
        "echo str_repeat('%s',5);",
        # Perl http://perldoc.perl.org/functions/eval.html
        "print '%s'x5",
        # Python http://docs.python.org/reference/simple_stmts.html#the-exec-statement
        "print '%s'*5",
        # ASP
        "Response.Write(new String(\"%s\",5))"
     )
    
    WAIT_OBJ = (
        # PHP http://php.net/sleep
        # Perl http://perldoc.perl.org/functions/sleep.html
        delay("sleep(%s);"),
        # Python http://docs.python.org/library/time.html#time.sleep
        delay("import time;time.sleep(%s);"),
        # It seems that ASP doesn't support sleep! A language without sleep...
        # is not a language!
        # http://classicasp.aspfaq.com/general/how-do-i-make-my-asp-page-pause-or-sleep.html
        # JSP takes the amount in miliseconds
        # http://java.sun.com/j2se/1.4.2/docs/api/java/lang/Thread.html#sleep(long)
        delay("Thread.sleep(%s);", mult=1000),
        # ASP.NET also uses miliseconds
        # http://msdn.microsoft.com/en-us/library/d00bd51t.aspx
        # Note: The Sleep in ASP.NET is uppercase
        delay("Thread.Sleep(%s);", mult=1000)
    )

    def __init__(self):
        AuditPlugin.__init__(self)

        # Create some random strings, which the plugin will use.
        # for the fuzz_with_echo
        self._rnd = rand_alpha(5)
        self._expected_result = self._rnd * 5
        
        # User configured parameters
        self._use_time_delay = True
        self._use_echo = True

    def audit(self, freq):
        '''
        Tests an URL for eval() user input injection vulnerabilities.
        @param freq: A FuzzableRequest
        '''
        if self._use_echo:
            self._fuzz_with_echo(freq)
        
        if self._use_time_delay:
            self._fuzz_with_time_delay(freq)

    def _fuzz_with_echo(self, freq):
        '''
        Tests an URL for eval() usage vulnerabilities using echo strings.
        @param freq: A FuzzableRequest
        '''
        orig_resp = self._uri_opener.send_mutant(freq)
        print_strings = [pstr % (self._rnd,) for pstr in self.PRINT_STRINGS]
            
        mutants = create_mutants(freq, print_strings, orig_resp=orig_resp)
        
        self._send_mutants_in_threads(self._uri_opener.send_mutant,
                                      mutants,
                                      self._analyze_echo)


    def _fuzz_with_time_delay(self, freq):
        '''
        Tests an URL for eval() usage vulnerabilities using time delays.
        @param freq: A FuzzableRequest
        '''
        fake_mutants = create_mutants(freq, ['',])
        self._tm.threadpool.map(self._test_delay, fake_mutants)
    
    def _test_delay(self, mutant):
        '''
        Try to delay the response and save a vulnerability if successful
        '''
        if self._has_bug(mutant):
            return

        for delay_obj in self.WAIT_OBJ:
            
            ed = exact_delay(mutant, delay_obj, self._uri_opener)
            success, responses = ed.delay_is_controlled()

            if success:
                v = vuln.vuln(mutant)
                v.setPluginName(self.get_name())
                v.set_id( [r.id for r in responses] )
                v.set_severity(severity.HIGH)
                v.set_name('eval() input injection vulnerability')
                v.set_desc('eval() input injection was found at: ' + mutant.found_at())
                kb.kb.append_uniq(self, 'eval', v)
                break
                        
    def _analyze_echo(self, mutant, response):
        '''
        Analyze results of the _send_mutant method that was sent in the
        _fuzz_with_echo method.
        '''
        eval_error_list = self._find_eval_result(response)
        for eval_error in eval_error_list:
            if not re.search(eval_error, mutant.get_original_response_body(), re.I):
                v = vuln.vuln(mutant)
                v.setPluginName(self.get_name())
                v.set_id(response.id)
                v.set_severity(severity.HIGH)
                v.set_name('eval() input injection vulnerability')
                v.set_desc('eval() input injection was found at: ' + mutant.found_at())
                kb.kb.append_uniq(self, 'eval', v)

    def end(self):
        '''
        This method is called when the plugin wont be used anymore.
        '''
        self.print_uniq(kb.kb.get('eval', 'eval'), 'VAR')

    def _find_eval_result(self, response):
        '''
        This method searches for the randomized self._rnd string in html's.

        @param response: The HTTP response object
        @return: A list of error found on the page
        '''
        res = []
        
        if self._expected_result in response.body.lower():
            msg = 'Verified eval() input injection, found the concatenated random string: "'
            msg += self._expected_result + '" in the response body. '
            msg += 'The vulnerability was found on response with id ' + str(response.id) + '.'
            om.out.debug(msg)
            res.append(self._expected_result)
            
        return res

    def get_options(self):
        '''
        @return: A list of option objects for this plugin.
        '''
        ol = OptionList()
        
        d = 'Use time delay (sleep() technique)'
        h = 'If set to True, w3af will checks insecure eval() usage by analyzing'
        h += ' of time delay result of script execution.'
        o = opt_factory('useTimeDelay', self._use_time_delay, d, 'boolean', help=h)
        ol.add(o)
        
        d = 'Use echo technique'
        h = 'If set to True, w3af will checks insecure eval() usage by grepping'
        h += ' result of script execution for test strings.'
        o = opt_factory('useEcho', self._use_echo, d, 'boolean', help=h)
        ol.add(o)
        
        return ol

    def set_options(self, options_list):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of get_options().

        @param OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        '''
        self._use_time_delay = options_list['useTimeDelay'].get_value()
        self._use_echo = options_list['useEcho'].get_value()

    def get_long_desc(self):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin finds eval() input injection vulnerabilities. These 
        vulnerabilities are found in web applications, when the developer passes
        user controled data to the eval() function. To check for vulnerabilities
        of this kind, the plugin sends an echo function with two randomized
        strings as a parameters (echo 'abc' + 'xyz') and if the resulting HTML
        matches the string that corresponds to the evaluation of the expression
        ('abcxyz') then a vulnerability has been found.
        '''
