#
# GEMENSAM MODUL FÖR FÄLTHANTERING
#

import cgi
import string
import sys # Just for debugging
import db # Just for db.escape used to escape SQL strings
import time

# Configuration

year_yy_break = 10 # Breakpt. between 20th and 21st century in two-digit years
year_yyyy_min = 1900 # Lowest accepted four-digit year
year_yyyy_max = 2099 # Highest accepted four-digit year

# Exceptions

class FieldException(Exception): pass
class FieldVirtualError(FieldException): pass

#
# Class for a collection of fields
#

class FieldSet:
    def __init__(self):
        self.__fields = {}

    def add_fields(self, field_list):
        for field in field_list:
            self.__fields[field.get_name()] = field
            field.bind_to_fieldset(self)

    def __getitem__(self, key):
        return self.__fields[key].get_value()
        
    def __setitem__(self, key, value):
        self.__fields[key].set_value(value)

    def set_option(self, key, option, value):
        self.__fields[key].set_option(option, value)

    def convert_to_sql(self, key):
        return self.__fields[key].convert_to_sql()
        
    def make_default(self):
        for k in self.__fields.keys():
            self.__fields[k].make_default()

    def output_to_tags(self, tags):
        for k in self.__fields.keys():
            self.__fields[k].output_to_tags(tags)

    def input_from_form(self, form, prefix = ""):
        all_ok = 1
        for k in self.__fields.keys():
            if self.__fields[k].input_from_form(form, prefix) is not None:
                all_ok = 0
        return all_ok

    def get_error(self, key):
        return self.__fields[key].get_error()
        
    def get_errors(self):
        errors = []
        for k in self.__fields.keys():
            error = self.__fields[k].get_error()
            if error is not None:
                name = self.__fields[k].get_display_name()
                errors.append("%s: %s" % (name, error))
        
        return errors

    def get_errors_ul(self):
        return "<ul>%s</ul>" % string.join(map(lambda x: "<li>"+x,
                                               self.get_errors()),
                                           "\n")
    
    def input_from_sql(self, dict, table = None):
        for k in self.__fields.keys():
            if not self.__fields[k].get_option("no_load",0):
                self.__fields[k].input_from_sql(dict, table)
            else:
                self.__fields[k].make_default()

    def output_to_sql_insert(self):
        # Manufacture the tail of an SQL "INSERT INTO"
        # statement:

        col_list = []
        val_list = []
        for k in self.__fields.keys():
            if not self.__fields[k].get_option("no_update",0):
                col_list.append(k)
                val_list.append(self.__fields[k].convert_to_sql())
        return "(%s) VALUES(%s)" % (string.join(col_list,","),
                                    string.join(val_list,","))

    def output_to_sql_update(self):
        # Manufacture the tail of an SQL "UPDATE"
        # statement:

        col_list = self.__fields.keys()
        asn_list = []
        for k in col_list:
            if not self.__fields[k].get_option("no_update",0):
                asn_list.append("%s=%s" % (k,self.__fields[k].convert_to_sql()))
        return string.join(asn_list,",")

#
# Classes for a single field
#
#

class Field:
    def __init__(self, name, **options):
        self._name = name
        self._fieldset = None
        self._value = None
        self._error = None
        self._form_value = None
        self._default = None # Note: a default given in options overrides this
        self.set_options(options)

    def bind_to_fieldset(self, fieldset):
        # FIXME: This causes a circular structure (which cannot be G.C:ed)
        # Provide a function to "unbind" when a fieldset is not longer used
        self._fieldset = fieldset

    def set_options(self, options):
        self._options = options
        
    def set_option(self, option, value):
        self._options[option] = value
        
    def get_option(self, option, default = None):
        return self._options.get(option, default)
        
    def get_name(self):
        return self._name

    def get_display_name(self):
        return self._options.get("displayname", self._name)

    def get_error(self):
        return self._error

    def get_value(self):
        return self._value
    
    def set_value(self, value):
        self._value = value
        self.error = None
        
    def make_default(self):
        self._value = self._options.get("default", self._default)
        self._error = None
        
    def output_to_tags(self, tags):
        # This function is called to output a field to HTML tags
        # Provide convert_to_tag() if possible, otherwise override
        # this function.

        if self._error is None:
            tags[self._name] = self.convert_to_tag()
        else:
            # _form_value is always a list. Output first element.
            # Classes that really understand multiple values will override
            tags[self._name] = cgi.escape(self._form_value[0])

    def convert_to_tag(self, form):
        # This should be overriden!
        raise FieldVirtualError

    def input_from_form(self, form, prefix):
        # This function is called to read data from a CGI form into
        # the field.  Provide convert_from_form() if possible,
        # otherwise override this function

        self._error = None
        name = prefix + self._name
        if self._options.get("no_input",0):
            # We should not input from the form to this field,
            # but we set it to avoid trouble with leaking data
            self._value = self._default
            return self._error
        
        if form.has_key(name):
            entry = form[name]
            if type(entry) == type([]):
                self._form_value = map(lambda x: x.value, entry)
            else:
                self._form_value = [form[name].value]
        else:
            self._form_value = [""]

        (self._value, self._error) = self.convert_from_form(self._form_value)

        return self._error
    
    def input_from_sql(self, dict, table):
        # This function is called to read data from an SQL result
        # dictionary into the field. Provice convert_from_sql if possible,
        # or override this function.

        key = table+"."+self._name
        if dict.has_key(key):
            value = dict[key]
        else:
            value = None

        self._value = self.convert_from_sql(value)
        self._error = None

    def convert_from_sql(self, str):
        # Convert data from SQL form to internal. We expect the database
        # module to deliver strings as string, so we should not need to
        # override this one for simple types.
        return str

    def convert_to_sql(self):
        # Convert data from internal to SQL form. Override!
        raise FieldVirtualError


class TextField(Field):
    def __init__(self, name, **options):
        Field.__init__(self, name) 
        self.set_options(options)
        self._default = ""
        
    def convert_to_tag(self):
        # FIXME: Perhaps apply option "upcase" on output too
        val = self._value

        # Option empty: a certain value should be translated into an empty field
        empty = self._options.get("empty", None)
        if empty and val == empty:
            val = ""
        return cgi.escape(val)
    
    def convert_from_form(self, value):
        # No multiple values here
        str = value[0]

        # User provided checker has precedence.
        input_checker = self._options.get("input_checker",None)
        if input_checker:
            return input_checker(str)

        # Option empty: an empty field should be translated into a certain value
        # N.B. You must do this yourself if you provide an input_checker above
        empty = self._options.get("empty", None)
        if empty:
            if str == "":
                str = empty
            elif self._options.get("not_empty",0):
                # Option not_empty only check if option empty is not present
                if str == "":
                    return (None,"får ej vara tomt")

        # UPPER CASE
        if self._options.get("upcase",0):
            str = string.upper(str)
        
        return (str, None)

    def convert_to_sql(self):
        return "'"+db.escape(str(self._value))+"'"

class HTMLField(TextField):
    def convert_to_tag(self):
        return self._value
            
class OnetimeField(TextField):
    def convert_to_tag(self):
        if self._options.get("no_input", 0):
            return TextField.convert_to_tag(self)
        else:
            return "<input type=\"text\" length=\"16\" name=\"%s\" value=\"%s\">" % (self._name, TextField.convert_to_tag(self))
        
class IntField(Field):
    def __init__(self, name, **options):
        Field.__init__(self, name)
        self.set_options(options)
        self._default = 0
        
    def convert_to_tag(self):
        empty = self._options.get("empty", None)
        if empty is not None and self._value == empty:
            return ""
        else:
            return str(self._value)
    
    def convert_from_form(self, value):
        # No multiple values here
        str = value[0]
        if str == "":
            empty = self._options.get("empty", None)
            if empty is not None:
                return (empty, None)
            else:
                return (None, "får ej vara tomt")
            
        try:
            num = string.atoi(str)
        except:
            return (None, "felaktigt tal")

        return self.check_integer(num)

    def check_integer(self, num):
        # Override this function in derived classes!

        min = self._options.get("min", None)
        if min is not None:
            if num < min:
                return (None, "lägsta tillåtna värde är %d" % min)

        max = self._options.get("max", None)
        if max is not None:
            if num > max:
                return (None, "högsta tillåtna värde är %d" % max)

        return (num, None)

    def convert_to_sql(self):
        return str(self._value)

class YearField(IntField):
    def __init__(self, name, **options):
        IntField.__init__(self, name)
        self.set_options(options)
        now = time.localtime(time.time())
        self._default = now[0]
        
    def check_integer(self, num):
        if num < 0:
            return (None, "årtal får ej vara negativa")
        elif num <= year_yy_break:
            return (num + 2000, None)
        elif num < 100:
            return (num + 1900, None)
        elif num < year_yyyy_min:
            return (None, "felaktigt årtal")
        elif num <= year_yyyy_max:
            return (num, None)
        else:
            return (None, "för stort årtal")

# Numeric database field (0 or 1), shown as HTML checkbox

class BoolField(Field):
    def __init__(self, name, **options):
        Field.__init__(self, name)
        self.set_options(options)
        self._default = 0

    def convert_to_tag(self):
        if self._value:
            return "CHECKED"
        else:
            return ""
    
    def input_from_form(self, form, prefix):
        self._error = None
        name = prefix + self._name
        
        if self._options.get("no_input",0):
            # We should not input from the form to this field,
            # but we set it to avoid trouble with leaking data
            self._value = self._default
            return self._error
        
        if form.has_key(name):
            self._form_value = [form[name].value]
            self._value = 1
        else:
            self._form_value = [""]
            self._value = 0

        return self._error
    
    def convert_from_sql(self, val):
        if val == 0 or val == "0":
            return 0
        else:
            return 1

    def convert_to_sql(self):
        return str(self._value)

# Database field representing a choice, shown as HTML select

# This base class handles multiple choice lists consisting of tuples, where
# each tuples contains tag and text

class ChoiceField(Field):
    def __init__(self, name, **options):
        Field.__init__(self, name)
        self.set_options(options)
        self._default = [""]

    def output_to_tags(self, tags):
        if self._error is None:
            tags[self._name] = self.convert_to_tag_explicit(self._value)
        else:
            tags[self._name] = self.convert_to_tag_explicit(self._form_value)

    def get_choices(self):
        choices = self._options["choices"][:]
        if self._options.has_key("last_value"):
            choices.append((str(self._options["last_value"]),
                            self._options["last_text"]))
        return choices

    def convert_to_tag_explicit(self, value):
        if type(value) == type([]):
            value_list = value
        else:
            value_list = [value]

        # Make list of possible choices
        choices = self.get_choices()

        # If the option output_as_text is set, we should
        # output text instead.
        if self._options.get("output_as_text", 0):
            res = []
            for alt in choices:
                (tag, text) = self.convert_alt_to_tag_text(alt)
                if tag in value_list:
                    res.append(text)
            return string.join(res, ", ")
        else:
            # Loop over choices, outputing OPTIONS.
            # Make the ones present in the value selected
            
            res = []
            for alt in choices: 
                (tag, text) = self.convert_alt_to_tag_text(alt)
    
                res.append(self.generate_option(tag, text, tag in value_list))
    
            # FIXME: What are we to do with parts of the value that are not
            # present in the options list? Currently, we ignore them!
    
            # Return text
            return string.join(res, "\n")

    def generate_option(self, tag, text, selected):
        # Override to generate options differently!
        if selected:
            seltxt = " SELECTED"
        else:
            seltxt = ""

        return "<OPTION VALUE=%s %s>%s" % (cgi.escape(tag),
                                           seltxt,
                                           cgi.escape(text))
            
    def convert_alt_to_tag_text(self, alt):
        # Override this if choices list is different
        # Here we handle (tag, text) or just text or just number
        if type(alt) == type((1,2)):
            return alt
        else:
            return (alt, alt)

    def convert_value_part_to_tag(self, value):
        # Override this to convert value to tag differently
        # Here we assume that tags are strings
        return value

    def convert_from_form(self, values):
        # Handle empty case
        if values == [""]:
            values = []

        # Option "nonempty":
        if self._options.get("nonempty",0) and len(values) == 0:
            return (None,"val måste göras")

        # Option "single" test
        if self._options.get("single",0):
            single = 1
            if len(values) > 1:
                return (None,"flera val samtidigt är inte tillåtet")
        else:
            single = 0
            
        # Calculate permitted tags
        ok_tags = []

        for alt in self.get_choices():
            (tag, text) = self.convert_alt_to_tag_text(alt)
            ok_tags.append(tag)

        # Check each value in the list against the permitted tags
        for value in values:
            value_tag = self.convert_value_part_to_tag(value)
            if not value_tag in ok_tags:
                return (None,'"%s" är inte ett giltigt val' % value)

        # Option "single" returns a single value, not a list
        if single:
            return (values[0], None)
        else:
            return (values, None)

    def convert_to_sql(self):
        return "'"+db.escape(str(self._value))+"'"

class RadioButtons(ChoiceField):
    def generate_option(self, tag, text, selected):
	if selected:
	    seltxt = " checked"
	else:
	    seltxt = ""
	return "<input type=\"radio\" name=\"%s\" value=\"%s\"  %s>"\
	       "%s</input>" % (cgi.escape(self._name),
			       cgi.escape(tag), 
			       seltxt,
			       cgi.escape(text))



# This derived class uses checkboxes to "simulate" a multiple select
# Options "single" and "nonempty" are not supported!

class CheckChoiceField(ChoiceField):

    def generate_option(self, tag, text, selected):
        # Override to generate options differently!
        if selected:
            seltxt = " CHECKED"
        else:
            seltxt = ""

        cbname = cgi.escape(self._name + "_" + tag)
        return "<INPUT TYPE=CHECKBOX NAME=%s %s>&nbsp;%s" % (\
            cbname, seltxt, cgi.escape(text))

    def input_from_form(self, form, prefix):
        self._error = None
        self._value = []
        
        if self._options.get("no_input",0):
            # We should not input from the form to this field,
            # but we set it to avoid trouble with leaking data
            self._value = self._default
            return self._error
        
        for alt in self.get_choices(): 
            (tag, text) = self.convert_alt_to_tag_text(alt)
            cbname = cgi.escape(prefix + self._name + "_" + tag)
            if form.has_key(cbname):
                self._value.append(tag)

        return self._error
    
