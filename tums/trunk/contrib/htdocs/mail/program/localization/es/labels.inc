<?php

/*
 +-----------------------------------------------------------------------+
 | language/es/labels.inc                                                |
 |                                                                       |
 | Language file of the RoundCube Webmail client                         |
 | Copyright (C) 2005, RoundQube Dev. - Switzerland                      |
 | Licensed under the GNU GPL                                            |
 |                                                                       |
 +-----------------------------------------------------------------------+
 | Author: David Grajal Blanco <dgrabla@gmail.com>                       |
 |         http://david.grajal.net                                       |
 +-----------------------------------------------------------------------+
 | Changelog:                                                            |
 |  - 6/2/2006 Translations of new features and improvements)            |
 |  - 17/9/2005 First release                                            |
 +-----------------------------------------------------------------------+

 $Id: labels.inc 282 2006-07-25 22:11:50Z thomasb $

*/

$labels = array();

// login page
$labels['welcome']   = 'Bienvenido a $product';
$labels['username']  = 'Nombre de usuario';
$labels['password']  = 'Contraseña';
$labels['server']    = 'Servidor';
$labels['login']     = 'Entrar';

// taskbar
$labels['logout']   = 'Cerrar sesión';
$labels['mail']     = 'E-Mail';
$labels['settings'] = 'Configuración';
$labels['addressbook'] = 'Contactos';

// mailbox names
$labels['inbox']  = 'Entrada';
$labels['drafts'] = 'Borradores';
$labels['sent']   = 'Enviados';
$labels['trash']  = 'Papelera';
$labels['junk']   = 'Basura';

// message listing
$labels['subject'] = 'Asunto';
$labels['from']    = 'Remitente';
$labels['to']      = 'Destinatario';
$labels['cc']      = 'Copia';
$labels['bcc']     = 'Bcc';
$labels['replyto'] = 'Responder';
$labels['date']    = 'Fecha';
$labels['size']    = 'Tamaño';
$labels['priority'] = 'Prioridad';
$labels['organization'] = 'Organización';

// aliases
$labels['reply-to'] = $labels['replyto'];

$labels['mailboxlist'] = 'Carpetas';
$labels['messagesfromto'] = 'Mensajes desde $from a $to de $count';
$labels['messagenrof'] = 'Mensaje $nr de $count';

$labels['moveto']   = 'mover a...';
$labels['download'] = 'descargar';

$labels['filename'] = 'Nombre del fichero';
$labels['filesize'] = 'Tamaño del fichero';

$labels['preferhtml'] = 'Prefiero HTML';
$labels['htmlmessage'] = 'Mensaje HTML';
$labels['prettydate'] = 'Fecha detallada';

$labels['addtoaddressbook'] = 'Añadir a contactos';

// weekdays short
$labels['sun'] = 'Dom';
$labels['mon'] = 'Lun';
$labels['tue'] = 'Mar';
$labels['wed'] = 'Mie';
$labels['thu'] = 'Jue';
$labels['fri'] = 'Vie';
$labels['sat'] = 'Sáb';

// weekdays long
$labels['sunday']    = 'Domingo';
$labels['monday']    = 'Lunes';
$labels['tuesday']   = 'Martes';
$labels['wednesday'] = 'Miercoles';
$labels['thursday']  = 'Jueves';
$labels['friday']    = 'Viernes';
$labels['saturday']  = 'Sábado';

$labels['today'] = 'Hoy';

// toolbar buttons
$labels['checkmail']        = 'Revisar si hay nuevos mensajes';
$labels['writenewmessage']  = 'Crear nuevo mensaje';
$labels['replytomessage']   = 'Responder al mensaje';
$labels['replytoallmessage'] = 'Responder al emisor y a todos los destinatarios';
$labels['forwardmessage']   = 'Reenviar mensaje';
$labels['deletemessage']    = 'Mover mensaje a la papelera';
$labels['printmessage']     = 'Imprimir este mensaje';
$labels['previousmessages'] = 'Mostrar mensajes anteriores';
$labels['nextmessages']     = 'Mostrar mensajes siguientes';
$labels['backtolist']       = 'Volver a la lista de mensajes';

$labels['viewsource']       = 'Mostrar código';

$labels['select'] = 'Seleccionar';
$labels['all'] = 'Todos';
$labels['none'] = 'Ninguno';
$labels['unread'] = 'No leidos';

$labels['compact'] = 'Compactar';
$labels['empty'] = 'Vaciar';
$labels['purge'] = 'Eliminar';

$labels['quota'] = 'Uso de disco';
$labels['unknown']  = 'desconocido';
$labels['unlimited']  = 'sin límite';

$labels['quicksearch']  = 'Búsqueda rápida';
$labels['resetsearch']  = 'Reajustar la búsqueda';


// message compose
$labels['compose']  = 'Escribir un mensaje';
$labels['savemessage']  = 'Almacenar como borrador';
$labels['sendmessage']  = 'Enviar ahora el mensaje';
$labels['addattachment']  = 'Añadir un fichero';
$labels['charset']  = 'Codigo';
$labels['returnreceipt'] = 'Recibo de entrega';

$labels['checkspelling'] = 'Revisar la ortografía';
$labels['resumeediting'] = 'Continuar el editaje';
$labels['revertto'] = 'Revertir a';

$labels['attachments'] = 'Adjuntos';
$labels['upload'] = 'Subir';
$labels['close']  = 'Cerrar';

$labels['low']     = 'Bajo';
$labels['lowest']  = 'Bajísimo';
$labels['normal']  = 'Normal';
$labels['high']    = 'Alto';
$labels['highest'] = 'Altísimo';


$labels['nosubject']  = '(sin asunto)';
$labels['showimages'] = 'Mostrar imágenes';


// address boook
$labels['name']      = 'Nombre completo';
$labels['firstname'] = 'Nombre';
$labels['surname']   = 'Apellido';
$labels['email']     = 'E-Mail';

$labels['edit']   = 'Editar';
$labels['cancel'] = 'Cancelar';
$labels['save']   = 'Almacenar';
$labels['delete'] = 'Eliminar';

$labels['newcontact']     = 'Crear nuevo contacto';
$labels['addcontact']     = 'Añadir nuevo contacto';
$labels['editcontact']    = 'Editar contacto';
$labels['deletecontact']  = 'Eliminar contactos seleccionados';
$labels['composeto']      = 'Redactar correo a';
$labels['contactsfromto'] = 'Contactos $from a $to de $count';
$labels['print']          = 'Imprimir';
$labels['export']         = 'Exportar';

$labels['previouspage']   = 'Mostrar grupo anterior';
$labels['nextpage']       = 'Mostrar grupo siguiente';

// LDAP search
$labels['ldapsearch'] = 'Búsqueda en el directorio LDAP';

$labels['ldappublicsearchname'] = 'Nombre';
$labels['ldappublicsearchtype'] = '¿Búsqueda exacta?';
$labels['ldappublicserverselect'] = 'Elegir servidores';
$labels['ldappublicsearchfield'] = 'Buscando';
$labels['ldappublicsearchform'] = 'Buscar un contacto';
$labels['ldappublicsearch'] = 'Buscar';


// settings
$labels['settingsfor']  = 'Configuración para';

$labels['preferences']  = 'Preferencias';
$labels['userpreferences']  = 'Preferencias de usuario';
$labels['editpreferences']  = 'Editar preferencias de usuario';

$labels['identities']  = 'Identidades';
$labels['manageidentities']  = 'Gestionar identidades para esta cuenta';
$labels['newidentity']  = 'Nueva identidad';

$labels['newitem']  = 'Nuevo';
$labels['edititem']  = 'Editar';

$labels['setdefault']  = 'Seleccionar opción por defecto';
$labels['language']  = 'Idioma';
$labels['timezone']  = 'Zona horaria';
$labels['pagesize']  = 'Filas por página';
$labels['signature'] = 'Firma';
$labels['dstactive']  = 'Cambio de horario';

$labels['folder']  = 'Carpeta';
$labels['folders']  = 'Carpetas';
$labels['foldername']  = 'Nombre de carpeta';
$labels['subscribed']  = 'Suscribirse';
$labels['create']  = 'Crear';
$labels['createfolder']  = 'Crear nueva carpeta';
$labels['rename'] = 'Renombrar';
$labels['renamefolder'] = 'Renombrar carpeta';
$labels['deletefolder']  = 'Eliminar carpeta';
$labels['managefolders']  = 'Gestionar carpetas';

$labels['sortby'] = 'Ordenar por';
$labels['sortasc']  = 'Orden ascendente';
$labels['sortdesc'] = 'Orden descendente';

?>