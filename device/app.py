# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# app.py - Application module
#
# Part of the AlpycaDevice Alpaca skeleton/template device driver
#
# Author:   Robert B. Denny <rdenny@dc3.com> (rbd)
#
# Python Compatibility: Requires Python 3.7 or later
# GitHub: https://github.com/ASCOMInitiative/AlpycaDevice
#

import sys
import traceback
import inspect
from wsgiref.simple_server import WSGIRequestHandler, make_server
from enum import IntEnum

# -- isort wants the above line to be blank --
# Controller classes (for routing)
import discovery
import exceptions
from falcon import Request, Response, App, HTTPInternalServerError
import management
import setup
import log
from config import Config
from discovery import DiscoveryResponder
from shr import set_shr_logger

#########################
# FOR EACH ASCOM DEVICE #
#########################
import telescope

#--------------
API_VERSION = 1
#--------------

class LoggingWSGIRequestHandler(WSGIRequestHandler):
    """Subclass of  WSGIRequestHandler allowing us to control WSGI server's logging"""

    def log_message(self, format: str, *args):
        """Log a message from within the Python **wsgiref** simple server

        Logging elsewhere logs the incoming request *before*
        processing in the responder, making it easier to read
        the overall log. The wsgi server calls this function
        at the end of processing. Normally the request would not
        need to be logged again. However, in order to assure
        logging of responses with HTTP status other than
        200 OK, we log the request again here.

        For more info see
        `this article <https://stackoverflow.com/questions/31433682/control-wsgiref-simple-server-log>`_

        Args:
            format  (str):   Unused, old-style format (see notes)
            args[0] (str):   HTTP Method and URI ("request")
            args[1] (str):   HTTP response status code
            args[2] (str):   HTTP response content-length


        Notes:
            * Logs using :py:mod:`log`, our rotating file logger ,
              rather than using stdout.
            * The **format** argument is an old C-style format for
              for producing NCSA Commmon Log Format web server logging.

        """

        ##TODO## If I enable this, the server occasionally fails to respond
        ##TODO## on non-200s, per Wireshark. So crazy!
        # if args[1] != '200':  # Log this only on non-200 responses
        #     log.logger.info(f'{self.client_address[0]} <- {format%args}')

#-----------------------
# Magic routing function
# ----------------------
def init_routes(app: App, devname: str, module):
    """Initialize Falcon routing from URI to responser classses

    Inspects a module and finds all classes, assuming they are Falcon
    responder classes, and calls Falcon to route the corresponding
    Alpaca URI to each responder. This is done by creating the
    URI template from the responder class name.

    Note that it is sufficient to create the controller instance
    directly from the type returned by inspect.getmembers() since
    the instance is saved within Falcon as its resource controller.
    The responder methods are called with an additional 'devno'
    parameter, containing the device number from the URI. Reject
    negative device numbers.

    Args:
        app (App): The instance of the Falcon processor app
        devname (str): The name of the device (e.g. 'rotator")
        module (module): Module object containing responder classes

    Notes:
        * The call to app.add_route() creates the single instance of the
          router class right in the call, as the second parameter.
        * The device number is extracted from the URI by using an
          **int** placeholder in the URI template, and also using
          a format converter to assure that the number is not
          negative. If it is, Falcon will send back an HTTP
          ``400 Bad Request``.

    """

    memlist = inspect.getmembers(module, inspect.isclass)
    for cname,ctype in memlist:
        # Only classes *defined* in the module and not the enum classes
        if ctype.__module__ == module.__name__ and not issubclass(ctype, IntEnum):
            app.add_route(f'/api/v{API_VERSION}/{devname}/{{devnum:int(min=0)}}/{cname.lower()}', ctype())  # type() creates instance!


def custom_excepthook(exc_type, exc_value, exc_traceback):
    """Last-chance exception handler

    Caution:
        Hook this as last-chance only after the config info
        has been initialized and the logger is set up!

    Assures that any unhandled exceptions are logged to our logfile.
    Should "never" be called since unhandled exceptions are
    theoretically caught in falcon. Well it's here so the
    exception has a chance of being logged to our file. It's
    used by :py:func:`~app.falcon_uncaught_exception_handler` to
    make sure exception info is logged instead of going to
    stdout.

    Args:
        exc_type (_type_): _description_
        exc_value (_type_): _description_
        exc_traceback (_type_): _description_

    Notes:
        * See the Python docs for `sys.excepthook() <https://docs.python.org/3/library/sys.html#sys.excepthook>`_
        * See `This StackOverflow article <https://stackoverflow.com/a/58593345/159508>`_
        * A config option provides for a full traceback to be logged.

    """
    # Do not print exception when user cancels the program
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    log.logger.error(f'An uncaught {exc_type.__name__} exception occurred:')
    log.logger.error(exc_value)

    if Config.verbose_driver_exceptions and exc_traceback:
        format_exception = traceback.format_tb(exc_traceback)
        for line in format_exception:
            log.logger.error(repr(line))


def falcon_uncaught_exception_handler(req: Request, resp: Response, ex: BaseException, params):
    """Handle Uncaught Exceptions while in a Falcon Responder

        This catches unhandled exceptions within the Falcon responder,
        logging the info to our log file instead of it being lost to
        stdout. Then it logs and responds with a 500 Internal Server Error.

    """
    exc = sys.exc_info()
    custom_excepthook(exc[0], exc[1], exc[2])
    raise HTTPInternalServerError(title='Internal Server Error', description='Alpaca endpoint responder failed. See logfile.')

# ===========
# APP STARTUP
# ===========
def main():
    """ Application startup"""
    logger = log.init_logging()
    # Share this logger throughout
    log.logger = logger
    exceptions.logger = logger
    discovery.logger = logger
    set_shr_logger(logger)

    #########################
    # FOR EACH ASCOM DEVICE #
    #########################
    telescope.logger = logger
    
    tel_dev = telescope.start_tel_device(logger)

    # -----------------------------
    # Last-Chance Exception Handler
    # -----------------------------
    sys.__excepthook__ = custom_excepthook

    # ---------
    # DISCOVERY
    # ---------
    _DSC = DiscoveryResponder(Config.ip_address, Config.port)

    # ----------------------------------
    # MAIN HTTP/REST API ENGINE (FALCON)
    # ----------------------------------
    # falcon.App instances are callable WSGI apps
    falc_app = App()
    #
    # Initialize routes for each endpoint the magic way
    #
    #########################
    # FOR EACH ASCOM DEVICE #
    #########################
    init_routes(falc_app, 'telescope', telescope)
    #
    # Initialize routes for Alpaca support endpoints
    falc_app.add_route('/management/apiversions', management.apiversions())
    falc_app.add_route(f'/management/v{API_VERSION}/description', management.description())
    falc_app.add_route(f'/management/v{API_VERSION}/configureddevices', management.configureddevices())
    falc_app.add_route('/setup', setup.svrsetup())
    falc_app.add_route(f'/setup/v{API_VERSION}/telescope/{{devnum}}/setup', setup.devsetup())

    #
    # Install the unhandled exception processor. See above,
    #
    falc_app.add_error_handler(Exception, falcon_uncaught_exception_handler)

    # ------------------
    # SERVER APPLICATION
    # ------------------
    # Using the lightweight built-in Python wsgi.simple_server
    with make_server(Config.ip_address, Config.port, falc_app, handler_class=LoggingWSGIRequestHandler) as httpd:
        logger.info(f'==STARTUP== Serving on {Config.ip_address}:{Config.port}. Time stamps are UTC.')
        # Serve until process is killed
        try:
            httpd.serve_forever()
        finally:
            logger.info('==SHUTDOWN== Server shutting down.')
            httpd.server_close()

# ========================
if __name__ == '__main__':
    print('Starting Alpaca Device Server')
    main()
# ========================
