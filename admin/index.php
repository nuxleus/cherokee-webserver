<?php /* -*- Mode: PHP; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*- */

/* Cherokee
 *
 * Authors:
 *      Alvaro Lopez Ortega <alvaro@alobbs.com>
 *
 * Copyright (C) 2001-2006 Alvaro Lopez Ortega
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of version 2 of the GNU General Public
 * License as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA
 */

require_once ('common.php');
require_once ('config_node.php');
require_once ('server.php');
require_once ('widget_debug.php');
require_once ('page_debug.php');


function read_configuration () {
	$conf = new ConfigNode();
	
	$ret = $conf->Load (cherokee_default_config_file);
	if ($ret != ret_ok) {
		PRINT_ERROR ("Couldn't read $default_config");
	}

	return $conf;
}

function main() 
{
	session_start();

	if ($_SESSION["config"] == null) {
		$conf = read_configuration ();
		$_SESSION["config"] = $conf;
	}

	$conf   = &$_SESSION["config"];
	$server = new Server($conf);

	$theme = new Theme();
	$page  = new PageDebug(&$theme, &$conf);

	echo $page->Render();

	session_write_close();
}

main();
?>