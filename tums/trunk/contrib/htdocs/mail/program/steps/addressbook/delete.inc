<?php

/*
 +-----------------------------------------------------------------------+
 | program/steps/addressbook/delete.inc                                  |
 |                                                                       |
 | This file is part of the RoundCube Webmail client                     |
 | Copyright (C) 2005, RoundCube Dev. - Switzerland                      |
 | Licensed under the GNU GPL                                            |
 |                                                                       |
 | PURPOSE:                                                              |
 |   Delete the submitted contacts (CIDs) from the users address book    |
 |                                                                       |
 +-----------------------------------------------------------------------+
 | Author: Thomas Bruederli <roundcube@gmail.com>                        |
 +-----------------------------------------------------------------------+

 $Id: delete.inc 88 2005-12-03 16:54:12Z roundcube $

*/

$REMOTE_REQUEST = TRUE;

if ($_GET['_cid'])
  {
  $DB->query("UPDATE ".get_table_name('contacts')."
              SET    del=1
              WHERE  user_id=?
              AND    contact_id IN (".$_GET['_cid'].")",
              $_SESSION['user_id']);
                     
  $count = $DB->affected_rows();
  if (!$count)
    {
    // send error message
    exit;
    }


  // count contacts for this user
  $sql_result = $DB->query("SELECT COUNT(contact_id) AS rows
                            FROM ".get_table_name('contacts')."
                            WHERE  del<>1
                            AND    user_id=?",
                            $_SESSION['user_id']);
                                   
  $sql_arr = $DB->fetch_assoc($sql_result);
  $rowcount = $sql_arr['rows'];    

  // update message count display
  $pages = ceil($rowcount/$CONFIG['pagesize']);
  $commands = sprintf("this.set_rowcount('%s');\n", rcmail_get_rowcount_text($rowcount));
  $commands .= sprintf("this.set_env('pagecount', %d);\n", $pages);


  // add new rows from next page (if any)
  if ($_GET['_from']!='show' && $pages>1 && $_SESSION['page'] < $pages)
    {
    $start_row = ($_SESSION['page'] * $CONFIG['pagesize']) - $count;

    // get contacts from DB
    $sql_result = $DB->limitquery("SELECT * FROM ".get_table_name('contacts')."
                                   WHERE  del<>1
                                   AND    user_id=?
                                   ORDER BY name",
                                   $start_row,
                                   $count,
                                   $_SESSION['user_id']);
                                     
    $commands .= rcmail_js_contacts_list($sql_result);

/*
    // define list of cols to be displayed
    $a_show_cols = array('name', 'email');
    
    while ($sql_arr = $DB->fetch_assoc($sql_result))
      {
      $a_row_cols = array();
            
      // format each col
      foreach ($a_show_cols as $col)
        {
        $cont = rep_specialchars_output($sql_arr[$col]);
        $a_row_cols[$col] = $cont;
        }
  
      $commands .= sprintf("this.add_contact_row(%s, %s);\n",
                           $sql_arr['contact_id'],
                           array2js($a_row_cols));
      }
*/
    }

  // send response
  rcube_remote_response($commands);
  }

exit;
?>