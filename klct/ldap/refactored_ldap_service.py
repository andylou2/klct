import os
import ssl
import subprocess
import socket
import sys
import logging
from collections import OrderedDict

import ldap3
import yaml
from ldap3 import Server, Connection, ALL
from ldap3.core.exceptions import LDAPStartTLSError

import klct.log.logger

LOG = logging.getLogger(__name__)


class LDAPServiceException(Exception):
    pass


class LDAPNetworkException(LDAPServiceException):
    pass


class LDAPConnectionException(LDAPServiceException):
    pass


class LDAPCertException(LDAPConnectionException):
    pass


class LDAPSocketBindException(LDAPConnectionException):
    pass


class LDAPConnectionClosedException(LDAPConnectionException):
    pass


class LDAPQueryException(LDAPConnectionException):
    pass


class NetworkValidator(object):
    def _check_valid_ip(self, host_name):
        """
        Checks if the given hostName is a valid IP address.
        Return True if valid, False if invalid.
        """
        try:
            socket.inet_aton(host_name)
            LOG.debug("{} is a valid host name".format(host_name))
            return True
        except socket.error:
            pass
        try:
            socket.inet_pton(socket.AF_INET6, host_name)
            LOG.debug("{} is a valid IPV6 address".format(host_name))
            return True
        except socket.error:
            LOG.warning("{} is an invalid host name".format(host_name))
            return False

    def ping_ldap_server(self, host_name):
        """
        Checks if the given hostName is valid, and pings it.
        """
        LOG.info("Initializing ping sequence to {}".format(host_name))
        new_host_name = ""
        try:
            new_host_name = socket.gethostbyname(host_name)
            LOG.debug("Converted {} to an ip: {}".format(host_name,
                                                         new_host_name))
        except socket.gaierror:
            LOG.debug("Unable to convert {}".format(host_name))
            pass

        is_valid = self._check_valid_ip(new_host_name)
        if not is_valid or host_name == "":
            message = "{} is an invalid host name".format(host_name)
            raise LDAPNetworkException(message)

        with open(os.devnull, "w"):
            try:
                subprocess.check_output(["ping", "-c", "1", host_name],
                                        stderr=subprocess.STDOUT,
                                        universal_newlines=True)
                LOG.debug("Successfully pinged {}".format(host_name))
            except subprocess.CalledProcessError:
                message = "Unsuccessfully pinged {}".format(host_name)
                LOG.warning(message)
                raise LDAPNetworkException(message)

        if host_name == new_host_name:
            return "ldap://{}".format(host_name)
        else:
            return host_name


class LDAPConnection(object):
    def __init__(self):
        self.conn = None
        self.server = None

    def connect_ldap_server(self, host_name, port_number=None, user_name=None,
                            password=None, want_tls='n', tls_cert_path=None):
        """
        Attempts to connect to the provided hostName and port number, default
        port is 389 if none provided, using the provided user name and pass.
        Sets up a connection given the parameters.
        Note: unbind the returned connection when finished using socket
        """
        LOG.info("Initializing connection to {}".format(host_name))
        if port_number is None and want_tls == 'n':
            LOG.debug("tls not requested, setting default port to 389")
            port_number = 389
        elif port_number is None and want_tls == 'y':
            LOG.debug("tls requested, setting default port to 636")
            port_number = 636
        try:
            LOG.debug("Attempting to create server object with port: {}, "
                      "username: {}, password: {}, tls_requested: {}, "
                      "certificate path: {}".format(
                str(port_number), str(user_name), str(password),
                want_tls, str(tls_cert_path)))
            if want_tls == 'n':
                self.server = Server(host_name, port=port_number, get_info=ALL)
            else:
                LOG.debug("Attempting to create tls object with "
                          "certificate file: {}".format(tls_cert_path))
                try:
                    subprocess.check_output(["openssl", "x509",
                                             "-checkend", "120", "-noout",
                                             "-in", tls_cert_path],
                                            stderr=subprocess.STDOUT,
                                            universal_newlines=True)
                    LOG.debug("Tls certificate is not expired")
                except subprocess.CalledProcessError:
                    message = "Tls certificate has expired " \
                              "or will expire within the next 2 minutes"
                    LOG.warning(message)
                    raise LDAPCertException(message)

                tls_object = ldap3.Tls(ca_certs_file=tls_cert_path,
                                       validate=ssl.CERT_REQUIRED)
                self.server = Server(host_name, port=port_number,
                                     use_ssl=True, tls=tls_object,
                                     get_info=ALL)
                LOG.debug("Successfully created tls object")
            LOG.debug("Successfully created server object")
            LOG.debug("Attempting to create connection socket")
            self.conn = Connection(self.server, user=user_name,
                                   password=password)
            LOG.debug("Successfully created socket")
            LOG.debug("Attempting to bind to socket")
            if not self.conn.bind():
                message = "Failed to bind to socket " \
                          "(Invalid Log in credentials)"
                LOG.warning(message)
                raise LDAPSocketBindException(message)
            LOG.debug("Successfully bound to socket")
            if want_tls == 'y':
                LOG.debug("Attempting to start tls on connection")
                self.conn.start_tls()
                LOG.debug("Successfully started tls")
            LOG.debug("Successfully connected!")
            return
        except ldap3.LDAPSocketOpenError:
            if port_number != 636 and want_tls == 'y':
                message = "Invalid socket: Connecting with TLS may " \
                          "require a different port number."
            else:
                message = "Failed to connect due to invalid socket."
        except ldap3.LDAPInvalidPortError:
            message = "Invalid Port"
        except ldap3.LDAPPasswordIsMandatoryError:
            message = "Please enter a password"
        except ldap3.core.exceptions.LDAPStartTLSError:
            message = "Unable to start TLS"
        LOG.debug(message)
        raise LDAPConnectionException(message)


class LDAPService(object):
    def __init__(self, conn, server):
        self.conn = conn
        self.server = server

    def _create_filter(self, attributes, num_attributes):
        """
        Returns a filter based on the number of attributes we want filtered.
        todo: add more number of attributes (currently only handles 3)
        """
        if num_attributes is 1:
            filter = "({}=*)".format(attributes[0])
        elif num_attributes is 2:
            filter = "(&(objectclass={})({}=*))".format(
                attributes[0], attributes[1])
        elif num_attributes is 3:
            filter = "(&(&({}={}))(objectclass={})({}=*))".format(
                attributes[0], attributes[1], attributes[2], attributes[3])
        LOG.debug("Created search filter: {}".format(filter))
        return filter


    def retrieve_server_info(self):
        """
        Retrieves the information related to the server passed in.
        """
        LOG.info("Attempting to retrieve server Info")
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)
        LOG.debug("Connection socket is open")
        LOG.debug("Creating serverinfo and serverschema files")

        orig_stdout = sys.stdout

        sys.stdout = open("serverinfo.txt", "w+")  # note: doesn't matter
        # that we overwrite serverinfo.txt bc users personal files should
        # never be in this directory
        print(self.server.info)
        sys.stdout.close()

        sys.stdout = open("serverschema.txt", "w+")
        print(self.server.schema)
        sys.stdout.close()

        sys.stdout = orig_stdout
        LOG.debug("Dumping server info and schema to the respective files")
        LOG.debug("Closing serverinfo and serverschema files")

        LOG.debug("Searching for ldap attributes")
        if self.conn.search('', '(objectclass=*)',
                            ldap3.SEARCH_SCOPE_BASE_OBJECT,
                            attributes=ldap3.ALL_ATTRIBUTES,
                            get_operational_attributes=True) is True \
                and self.conn.entries:
            version = ""
            i = 0
            try:
                version_result = self.server.info.supported_ldap_versions
                for i in range(len(version_result) - 1):
                    version = "{} {}, ".format(version, str(version_result[i]))
                if len(version_result) == 1:
                    version = "{} {}".format(version, str(version_result[i]))
                else:
                    version = "{} {}".format(version, str(
                        version_result[i + 1]))
                LOG.debug("Found supported ldap versions: {}".format(version))
            except:
                LOG.warning("Unable to find supported ldap versions")
                version = "N/A"
            try:
                server_type = self.conn.response[0]['attributes']['structuralObjectClass']
                LOG.debug("Found ldap server type: {}".format(server_type))
            except:
                if str(self.server.info).lower().find("microsoft") != -1 \
                        and str(self.server.info).lower().find(
                            "active directory") != -1:
                    LOG.debug("Found ldap server type: Active Directory")
                    server_type = "Active Directory"
                else:
                    LOG.warning("Unable to find ldap server type")
                    server_type = "No server type found. " \
                                  "(This usually means the server type is AD)"
            return {'version': "Supported LDAP Version: {}".format(version),
                    'type': "LDAP Server Type: {}".format(server_type)}
        else:
            message = "Unable to find information in the LDAP server"
            LOG.debug(message)
            raise LDAPQueryException(message)

    def get_ldap_suffix(self):
        """
        Returns the base dn of the ldap server
        """
        LOG.info("Discovering suffix (base DN) from server information")
        try:
            base_dn = str(self.server.info.naming_contexts[0])
            LOG.debug("Found suffix (base DN): {}".format(base_dn))
            return base_dn
        except:
            message = "Unable to find suffix (base DN)"
            LOG.warning(message)
            raise LDAPQueryException(message)

    def check_ldap_suffix(self, base_dn):
        """
        Checks that the given base_dn is the correct suffix for the given
        connection.
        """
        LOG.info("Validating given base suffix (base DN): {}".format(base_dn))
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")
        search_filter = self._create_filter(['cn'], 1)
        if self.conn.search(search_base=base_dn, search_filter=search_filter) \
                is True and self.conn.entries:
            LOG.debug("{} is a valid suffix (base DN)".format(base_dn))
            return True
        else:
            message = "{} is an invalid suffix (base DN)".format(base_dn)
            LOG.warning(message)
            raise LDAPQueryException(message)

    def validate_info(self, dn, id_attribute, name_attribute):
        """
        Checks that the given dn is valid. If so, it will validate the
        id_attribute and name_attribute as well.
        """
        LOG.info("Validating given DN: {}".format(dn))
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")

        if self.conn.search(search_base=dn, search_scope=ldap3.LEVEL,
                            search_filter='(objectclass=*)',
                            attributes=[ldap3.ALL_ATTRIBUTES],
                            size_limit=1) is True and self.conn.entries:
            LOG.debug("{} is a valid DN".format(dn))
            ret_message = None
            if id_attribute in self.conn.entries[0]:
                LOG.debug("{} is a valid id attribute".format(id_attribute))
            else:
                message = "{} is an invalid id attribute".format(id_attribute)
                LOG.warning(message)
                raise LDAPQueryException
            if name_attribute in self.conn.entries[0]:
                LOG.debug("{} is a valid name attribute".format(
                    name_attribute))
            else:
                message = "{} is an invalid name attribute".format(
                    name_attribute)
                LOG.warning(message)
                if ret_message is None:
                    ret_message = message
                else:
                    ret_message = "{}, {} is an invalid name attribute".format(
                        ret_message, name_attribute)
                raise LDAPQueryException(ret_message)
            if ret_message is None:
                ret_message = "{}, {}, and {} are valid".format(dn,
                                                                id_attribute,
                                                                name_attribute)
                return ret_message
        else:
            message = "{} is an invalid DN".format(dn)
            LOG.debug(message)
            raise LDAPQueryException(message)

    def list_object_classes(self, dn, id_attribute):
        """
        Returns a list of the object classes.
        """
        LOG.info("Searching for object classes")
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")
        search_filter = self._create_filter([id_attribute], 1)
        if self.conn.search(search_base=dn, search_scope=ldap3.LEVEL,
                            search_filter=search_filter,
                            attributes=['objectclass']) is True \
                and self.conn.entries:
            objclasses_list = []
            for objclass_list in self.conn.entries:
                for objclass in objclass_list.objectclass:
                    if objclass not in objclasses_list:
                        objclasses_list.append(objclass)
            LOG.debug("Found object classes: {}".format(str(objclasses_list)))
            return objclasses_list
        else:
            message = "No object classes found"
            LOG.warning(message)
            raise LDAPQueryException(message)

    def validate_object_class(self, dn, objectclass):
        LOG.info("Searching for object classes")
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")
        search_filter = '(objectclass=' + objectclass + ')'
        if self.conn.search(search_base=dn, search_filter=search_filter,
                            size_limit=1) is True and self.conn.entries:
            message = "{} is a valid objectclass".format(objectclass)
            LOG.debug(message)
            return message
        else:
            message = "{} is an invalid objectclass".format(objectclass)
            LOG.debug(message)
            raise LDAPQueryException(message)

    def list_entries(self, dn, id_attribute, name_attribute, objectclass,
                     limit):
        """
        Lists the entries, up to the limit.
        """
        LOG.info("Searching for a list of users")
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")
        if limit is None:
            LOG.debug("No limit entered, using 3 as default")
            limit = 3
        search_filter = self._create_filter([objectclass, id_attribute], 2)
        if self.conn.search(search_base=dn, search_scope=ldap3.LEVEL,
                            search_filter=search_filter,
                            attributes=[name_attribute],
                            size_limit=limit) is True and self.conn.entries:
            LOG.debug("Found list of entries: {}".format(
                str(self.conn.entries)))
            return self.conn.entries
        else:
            message = "No entries found"
            LOG.warning(message)
            raise LDAPQueryException(message)

    def get_entry(self, dn, id_attribute, objectclass, name_attribute, name):
        """
        Returns a specific user.
        """
        LOG.info("Searching for entry: {}".format(name))
        if self.conn.closed is True:
            message = "Connection socket is closed"
            LOG.debug(message)
            raise LDAPConnectionClosedException(message)

        LOG.debug("Connection is open")
        search_filter = self._create_filter([name_attribute, name, objectclass,
                                             id_attribute], 3)
        if self.conn.search(search_base=dn, search_filter=search_filter,
                            attributes=[id_attribute, name_attribute]) is \
                True and self.conn.entries:
            if len(self.conn.entries) > 1:
                message = "Duplicate entries found for: {}".format(name)
                LOG.warning(message)
                raise LDAPQueryException(message)
            LOG.debug("Found entry: {}".format(str(self.conn.entries)))
            return self.conn.entries
        else:
            message = "Entry: {} not found".format(name)
            LOG.warning(message)
            raise LDAPQueryException(message)


class FileValidator(object):
    def __init__(self, path):
        self.path = path

    def validate_file_write(self):
        try:
            fp = open(self.path, 'w')
            return fp
        except IOError:
            message = "Unable to open file: {} for writing.".format(self.path)
            LOG.warning(message)
            raise IOError(message)

    def validate_file_read(self):
        try:
            fp = open(self.path, 'r')
            return fp
        except IOError:
            message = "Unable to open file: {} for reading".format(
                str(self.path))
            LOG.debug(message)
            raise IOError(message)


class HOSYamlDump(object):
    def _ordered_dump(self, data, stream=None, Dumper=yaml.Dumper, **kwds):
        class OrderedDumper(Dumper):
            pass

        def _dict_representer(dumper, data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data.items())

        def _str_representer(dumper, data):
            if len(data.splitlines()) > 1:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data,
                                               style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        OrderedDumper.add_representer(OrderedDict, _dict_representer)
        OrderedDumper.add_representer(str, _str_representer)
        return yaml.dump(data, stream, OrderedDumper, **kwds)

    def save_config(self, data, path, name="ad"):
        """
        Saves the passed in dictionary data to the specified file
        """
        if path is None:
            return self._ordered_dump(data, path, Dumper=yaml.SafeDumper,
                                      default_flow_style=False)
        LOG.info("Saving configuration options to file.")
        f = FileValidator(path)
        fp = f.validate_file_write()

        if 'tls_cacertfile' in data:
            f = FileValidator(data['tls_cacertfile'])
            cert_fp = f.validate_file_read()
            cert = cert_fp.read()
            cert_dict = {'cacert': cert}
            cert_fp.close()
        else:
            cert_dict = {'cacert': "-----BEGIN CERTIFICATE-----\ncertificate"
                                   " appears here\n-----END CERTIFICATE-----"}

        LOG.debug("Dumping configuration options: {} to file: {}".format(
            str(data), path))
        dm_dict = OrderedDict([('name', name),
                               ('description',
                                "Dedicated domain for {} users".format(name))])
        conf_dict = OrderedDict([('identity',
                                  OrderedDict([('driver', "ldap")])),
                                 ('ldap', data)])
        od = OrderedDict([('keystone_domainldap_conf',
                           OrderedDict([('cert_settings', cert_dict),
                                        ('domain_settings', dm_dict),
                                        ('conf_settings', conf_dict)]))])
        self._ordered_dump(od, fp, Dumper=yaml.SafeDumper,
                           default_flow_style=False)
        fp.close()
        return "Data successfully dumped into {}".format(path)