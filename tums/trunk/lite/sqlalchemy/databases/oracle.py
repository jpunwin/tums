# oracle.py
# Copyright (C) 2005,2006 Michael Bayer mike_mp@zzzcomputing.com
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


import sys, StringIO, string

import sqlalchemy.util as util
import sqlalchemy.sql as sql
import sqlalchemy.engine as engine
import sqlalchemy.engine.default as default
import sqlalchemy.schema as schema
import sqlalchemy.ansisql as ansisql
import sqlalchemy.types as sqltypes
import sqlalchemy.exceptions as exceptions

try:
    import cx_Oracle
except:
    cx_Oracle = None
        
class OracleNumeric(sqltypes.Numeric):
    def get_col_spec(self):
        return "NUMERIC(%(precision)s, %(length)s)" % {'precision': self.precision, 'length' : self.length}
class OracleInteger(sqltypes.Integer):
    def get_col_spec(self):
        return "INTEGER"
class OracleSmallInteger(sqltypes.Smallinteger):
    def get_col_spec(self):
        return "SMALLINT"
class OracleDateTime(sqltypes.DateTime):
    def get_col_spec(self):
        return "DATE"
# Note:
# Oracle DATE == DATETIME
# Oracle does not allow milliseconds in DATE
# Oracle does not support TIME columns

class OracleText(sqltypes.TEXT):
    def get_col_spec(self):
        return "CLOB"
class OracleString(sqltypes.String):
    def get_col_spec(self):
        return "VARCHAR(%(length)s)" % {'length' : self.length}
class OracleChar(sqltypes.CHAR):
    def get_col_spec(self):
        return "CHAR(%(length)s)" % {'length' : self.length}
class OracleBinary(sqltypes.Binary):
    def get_col_spec(self):
        return "BLOB"
class OracleBoolean(sqltypes.Boolean):
    def get_col_spec(self):
        return "BOOLEAN"
        
colspecs = {
    sqltypes.Integer : OracleInteger,
    sqltypes.Smallinteger : OracleSmallInteger,
    sqltypes.Numeric : OracleNumeric,
    sqltypes.Float : OracleNumeric,
    sqltypes.DateTime : OracleDateTime,
    sqltypes.Date : OracleDateTime,
    sqltypes.String : OracleString,
    sqltypes.Binary : OracleBinary,
    sqltypes.Boolean : OracleBoolean,
    sqltypes.TEXT : OracleText,
    sqltypes.CHAR: OracleChar,
}


ischema_names = {
    'VARCHAR2' : OracleString,
    'DATE' : OracleDateTime,
    'DATETIME' : OracleDateTime,
    'NUMBER' : OracleNumeric,
    'BLOB' : OracleBinary,
    'CLOB' : OracleText
}

constraintSQL = """SELECT
  ac.constraint_name,
  ac.constraint_type,
  LOWER(loc.column_name) AS local_column,
  LOWER(rem.table_name) AS remote_table,
  LOWER(rem.column_name) AS remote_column
FROM all_constraints ac,
  all_cons_columns loc,
  all_cons_columns rem
WHERE ac.table_name = :table_name
AND ac.constraint_type IN ('R','P')
AND ac.owner = loc.owner
AND ac.constraint_name = loc.constraint_name
AND ac.r_owner = rem.owner(+)
AND ac.r_constraint_name = rem.constraint_name(+)
-- order multiple primary keys correctly
ORDER BY ac.constraint_name, loc.position"""


def descriptor():
    return {'name':'oracle',
    'description':'Oracle',
    'arguments':[
        ('dsn', 'Data Source Name', None),
        ('user', 'Username', None),
        ('password', 'Password', None)
    ]}

class OracleExecutionContext(default.DefaultExecutionContext):
    pass
    
class OracleDialect(ansisql.ANSIDialect):
    def __init__(self, use_ansi=True, module=None, threaded=True, **kwargs):
        self.use_ansi = use_ansi
        self.threaded = threaded
        if module is None:
            self.module = cx_Oracle
        else:
            self.module = module
        ansisql.ANSIDialect.__init__(self, **kwargs)

    def dbapi(self):
        return self.module

    def create_connect_args(self, url):
        if url.database:
            # if we have a database, then we have a remote host
            port = url.port
            if port:
                port = int(port)
            else:
                port = 1521
            dsn = self.module.makedsn(url.host,port,url.database)
        else:
            # we have a local tnsname
            dsn = url.host
        opts = dict(
            user=url.username,
            password=url.password,
            dsn = dsn,
            threaded = self.threaded
            )
        return ([], opts)
        
    def type_descriptor(self, typeobj):
        return sqltypes.adapt_type(typeobj, colspecs)

    def oid_column_name(self):
        return "rowid"

    def create_execution_context(self):
        return OracleExecutionContext(self)

    def compiler(self, statement, bindparams, **kwargs):
        return OracleCompiler(self, statement, bindparams, **kwargs)
    def schemagenerator(self, *args, **kwargs):
        return OracleSchemaGenerator(*args, **kwargs)
    def schemadropper(self, *args, **kwargs):
        return OracleSchemaDropper(*args, **kwargs)
    def defaultrunner(self, engine, proxy):
        return OracleDefaultRunner(engine, proxy)


    def has_table(self, connection, table_name):
        cursor = connection.execute("""select table_name from all_tables where table_name=:name""", {'name':table_name.upper()})
        return bool( cursor.fetchone() is not None )
        
    def reflecttable(self, connection, table):
        c = connection.execute ("select COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE, DATA_DEFAULT from ALL_TAB_COLUMNS where TABLE_NAME = :table_name", {'table_name':table.name.upper()})
        
        found_table = False
        while True:
            row = c.fetchone()
            if row is None:
                break
            found_table = True

            #print "ROW:" , row
            (name, coltype, length, precision, scale, nullable, default) = (row[0], row[1], row[2], row[3], row[4], row[5]=='Y', row[6])

            # INTEGER if the scale is 0 and precision is null
            # NUMBER if the scale and precision are both null
            # NUMBER(9,2) if the precision is 9 and the scale is 2
            # NUMBER(3) if the precision is 3 and scale is 0
            #length is ignored except for CHAR and VARCHAR2
            if coltype=='NUMBER' :
                if precision is None and scale is None:
                    coltype = OracleNumeric
                elif precision is None and scale == 0  :
                    coltype = OracleInteger
                else :
                    coltype = OracleNumeric(precision, scale)
            elif coltype=='CHAR' or coltype=='VARCHAR2':
                coltype = ischema_names.get(coltype, OracleString)(length)
            else:
                coltype = ischema_names.get(coltype)
               
            colargs = []
            if default is not None:
                colargs.append(schema.PassiveDefault(sql.text(default)))
            
            name = name.lower()
            
            table.append_item (schema.Column(name, coltype, nullable=nullable, *colargs))

        if not found_table:
            raise exceptions.NoSuchTableError(table.name)
        
        c = connection.execute(constraintSQL, {'table_name' : table.name.upper()})
        while True:
            row = c.fetchone()
            if row is None:
                break
            #print "ROW:" , row                
            (cons_name, cons_type, local_column, remote_table, remote_column) = row
            if cons_type == 'P':
                table.c[local_column]._set_primary_key()
            elif cons_type == 'R':
                table.c[local_column].append_item(
                    schema.ForeignKey(schema.Table(remote_table,
                                            table.metadata,
                                            autoload=True).c[remote_column]
                                      )
                    )

    def do_executemany(self, c, statement, parameters, context=None):
        rowcount = 0
        for param in parameters:
            c.execute(statement, param)
            rowcount += c.rowcount
        if context is not None:
            context._rowcount = rowcount

class OracleCompiler(ansisql.ANSICompiler):
    """oracle compiler modifies the lexical structure of Select statements to work under 
    non-ANSI configured Oracle databases, if the use_ansi flag is False."""
    
    def default_from(self):
        """called when a SELECT statement has no froms, and no FROM clause is to be appended.  
        gives Oracle a chance to tack on a "FROM DUAL" to the string output. """
        return " FROM DUAL"

    def apply_function_parens(self, func):
        return len(func.clauses) > 0

    def visit_join(self, join):
        if self.dialect.use_ansi:
            return ansisql.ANSICompiler.visit_join(self, join)
        
        self.froms[join] = self.get_from_text(join.left) + ", " + self.get_from_text(join.right)
        self.wheres[join] = sql.and_(self.wheres.get(join.left, None), join.onclause)

        if join.isouter:
            # if outer join, push on the right side table as the current "outertable"
            self._outertable = join.right

            # now re-visit the onclause, which will be used as a where clause
            # (the first visit occured via the Join object itself right before it called visit_join())
            join.onclause.accept_visitor(self)

            self._outertable = None

        self.visit_compound(self.wheres[join])
       
    def visit_alias(self, alias):
	"""oracle doesnt like 'FROM table AS alias'.  is the AS standard SQL??"""
        self.froms[alias] = self.get_from_text(alias.original) + " " + alias.name
        self.strings[alias] = self.get_str(alias.original)
 
    def visit_column(self, column):
        ansisql.ANSICompiler.visit_column(self, column)
        if not self.dialect.use_ansi and getattr(self, '_outertable', None) is not None and column.table is self._outertable:
            self.strings[column] = self.strings[column] + "(+)"
       
    def visit_insert(self, insert):
        """inserts are required to have the primary keys be explicitly present.
         mapper will by default not put them in the insert statement to comply
         with autoincrement fields that require they not be present.  so, 
         put them all in for all primary key columns."""
        for c in insert.table.primary_key:
            if not self.parameters.has_key(c.key):
                self.parameters[c.key] = None
        return ansisql.ANSICompiler.visit_insert(self, insert)

    def visit_select(self, select):
        """looks for LIMIT and OFFSET in a select statement, and if so tries to wrap it in a 
        subquery with row_number() criterion."""
        # TODO: put a real copy-container on Select and copy, or somehow make this
        # not modify the Select statement
        if getattr(select, '_oracle_visit', False):
            # cancel out the compiled order_by on the select
            if hasattr(select, "order_by_clause"):
                self.strings[select.order_by_clause] = ""
            ansisql.ANSICompiler.visit_select(self, select)
            return

        if select.limit is not None or select.offset is not None:
            select._oracle_visit = True
            # to use ROW_NUMBER(), an ORDER BY is required. 
            orderby = self.strings[select.order_by_clause]
            if not orderby:
                orderby = select.oid_column
                orderby.accept_visitor(self)
                orderby = self.strings[orderby]
            select.append_column(sql.ColumnClause("ROW_NUMBER() OVER (ORDER BY %s)" % orderby).label("ora_rn"))
            limitselect = sql.select([c for c in select.c if c.key!='ora_rn'])
            if select.offset is not None:
                limitselect.append_whereclause("ora_rn>%d" % select.offset)
                if select.limit is not None:
                    limitselect.append_whereclause("ora_rn<=%d" % (select.limit + select.offset))
            else:
                limitselect.append_whereclause("ora_rn<=%d" % select.limit)
            limitselect.accept_visitor(self)
            self.strings[select] = self.strings[limitselect]
            self.froms[select] = self.froms[limitselect]
        else:
            ansisql.ANSICompiler.visit_select(self, select)
            
    def limit_clause(self, select):
        return ""

class OracleSchemaGenerator(ansisql.ANSISchemaGenerator):
    def get_column_specification(self, column, **kwargs):
        colspec = column.name
        colspec += " " + column.type.engine_impl(self.engine).get_col_spec()
        default = self.get_column_default_string(column)
        if default is not None:
            colspec += " DEFAULT " + default

        if not column.nullable:
            colspec += " NOT NULL"
        return colspec

    def visit_sequence(self, sequence):
        self.append("CREATE SEQUENCE %s" % sequence.name)
        self.execute()

class OracleSchemaDropper(ansisql.ANSISchemaDropper):
    def visit_sequence(self, sequence):
        self.append("DROP SEQUENCE %s" % sequence.name)
        self.execute()

class OracleDefaultRunner(ansisql.ANSIDefaultRunner):
    def exec_default_sql(self, default):
        c = sql.select([default.arg], from_obj=["DUAL"], engine=self.engine).compile()
        return self.proxy(str(c), c.get_params()).fetchone()[0]
    
    def visit_sequence(self, seq):
        return self.proxy("SELECT " + seq.name + ".nextval FROM DUAL").fetchone()[0]

dialect = OracleDialect
