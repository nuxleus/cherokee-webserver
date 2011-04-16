/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*- */

/* Cherokee
 *
 * Authors:
 *      Alvaro Lopez Ortega <alvaro@alobbs.com>
 *
 * Copyright (C) 2001-2010 Alvaro Lopez Ortega
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
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
 * 02110-1301, USA.
 */

#include "common-internal.h"
#include "flcache.h"
#include "connection-protected.h"
#include "handler_file.h"
#include "server-protected.h"
#include "plugin_loader.h"
#include "util.h"
#include "avl_flcache.h"
#include "dtm.h"

#define ENTRIES "flcache"

#define FILES_PER_DIR 100


/* Front Line Cache
 */

ret_t
cherokee_flcache_new (cherokee_flcache_t **flcache)
{
	ret_t ret;
	CHEROKEE_NEW_STRUCT (n, flcache);

	ret = cherokee_avl_flcache_init (&n->request_map);
	if (ret != ret_ok) return ret;

	n->last_file_id = 0;
	cherokee_buffer_init (&n->local_directory);

	*flcache = n;
	return ret_ok;
}

ret_t
cherokee_flcache_free (cherokee_flcache_t *flcache)
{
	cherokee_buffer_mrproper (&flcache->local_directory);
	cherokee_avl_flcache_mrproper (&flcache->request_map, NULL);

	free (flcache);
	return ret_ok;
}

ret_t
cherokee_flcache_configure (cherokee_flcache_t     *flcache,
			    cherokee_config_node_t *conf,
			    void                   *vsrv)
{
	ret_t                      ret;
	cherokee_virtual_server_t *vserver = vsrv;

	/* Beware: conf might be NULL */
	UNUSED(conf);

	cherokee_buffer_add_str    (&flcache->local_directory, CHEROKEE_FLCACHE "/");
	cherokee_buffer_add_buffer (&flcache->local_directory, &vserver->name);

	ret = cherokee_mkdir_p_perm (&flcache->local_directory, 0700, W_OK);
	if (ret != ret_ok) {
		LOG_CRITICAL (CHEROKEE_ERROR_FLCACHE_MKDIR, flcache->local_directory.buf, "write");
		return ret;
	}

	TRACE (ENTRIES, "Created %s\n", flcache->local_directory.buf);
	return ret_ok;
}


ret_t
cherokee_flcache_req_get_cached (cherokee_flcache_t    *flcache,
				 cherokee_connection_t *conn)
{
	ret_t                        ret;
	cherokee_avl_flcache_node_t *entry = NULL;

	/* Check the cache
	 */
	ret = cherokee_avl_flcache_get (&flcache->request_map, conn, &entry);
	if ((ret != ret_ok) || (entry == NULL)) {
		TRACE (ENTRIES, "Front Line Cache: miss; '%s'\n", conn->request.buf);
		return ret_not_found;
	}

	/* Is it being stored?
	 */
	if (entry->status != flcache_status_ready) {
		TRACE (ENTRIES, "Front Line Cache: almost-hit; '%s' being cached (%d refs)\n",
		       conn->request.buf, entry->ref_count);
		return ret_deny;
	}

	/* Is it fresh enough?
	 */
	if (entry->valid_until < cherokee_bogonow_now) {
		TRACE (ENTRIES, "Front Line Cache: almost-hit; '%s' expired already (%d refs)\n",
		       conn->request.buf, entry->ref_count);

		if (entry->ref_count == 0) {
			cherokee_flcache_del_entry (flcache, entry);
		}

		return ret_deny;
	}

	/* Cache hit
	 */
	TRACE (ENTRIES, "Front Line Cache: hit; '%s' -> '%s' (%d refs)\n",
	       conn->request.buf, entry->file.buf, entry->ref_count);

	/* Open the cached file
	 */
	conn->flcache.fd = cherokee_open (entry->file.buf, O_RDONLY | O_NOFOLLOW, 0);
	if (unlikely (conn->flcache.fd == -1)) {
		return ret_error;
	}

	/* Store the reference to the object
	 */
	CHEROKEE_MUTEX_LOCK (&entry->ref_count_mutex);
	entry->ref_count += 1;
	CHEROKEE_MUTEX_UNLOCK (&entry->ref_count_mutex);

	conn->flcache.avl_node_ref = entry;
	conn->flcache.mode         = flcache_mode_out;

	return ret_ok;
}


ret_t
cherokee_flcache_req_is_storable (cherokee_flcache_t    *flcache,
				  cherokee_connection_t *conn)
{
	UNUSED (flcache);

	/* HTTP Method
	 */
	if (conn->header.method != http_get) {
		TRACE (ENTRIES, "Not storable: method(%d) != GET\n", conn->header.method);
		return ret_deny;
	}

	/* HTTPs
	 */
	if (conn->socket.is_tls == TLS) {
		TRACE (ENTRIES, "Not storable: Connection is %s\n", "TLS");
		return ret_deny;
	}

	/* Authenticated
	 */
	if (conn->validator != NULL) {
		TRACE (ENTRIES, "Not storable: Content requires %s\n", "authentication");
		return ret_deny;
	}

	/* Expiration
	 */
	if (conn->expiration == cherokee_expiration_epoch) {
		TRACE (ENTRIES, "Not storable: Alredy expired at '%s'\n", "epoch");
		return ret_deny;
	}

	if ((conn->expiration_prop & cherokee_expiration_prop_no_cache) ||
	    (conn->expiration_prop & cherokee_expiration_prop_no_store) ||
	    (conn->expiration_prop & cherokee_expiration_prop_must_revalidate) ||
	    (conn->expiration_prop & cherokee_expiration_prop_proxy_revalidate))
	{
		TRACE (ENTRIES, "Not storable: Expiration props: %d\n", conn->expiration_prop);
		return ret_deny;
	}

	/* Range
	 */
	if ((conn->range_end != -1) || (conn->range_start != -1)) {
		TRACE (ENTRIES, "Not storable: Requested a range (%d, %d)\n", conn->range_start, conn->range_end);
		return ret_deny;
	}

	TRACE (ENTRIES, "Request can be %s\n", "stored");
	return ret_ok;
}


/* Front-line cache connection
 */


ret_t
cherokee_flcache_conn_init (cherokee_flcache_conn_t *flcache_conn)
{
	flcache_conn->header_sent   = 0;
	flcache_conn->response_sent = 0;
	flcache_conn->avl_node_ref  = NULL;
	flcache_conn->mode          = flcache_mdoe_undef;
	flcache_conn->fd            = -1;

	cherokee_buffer_init (&flcache_conn->header);

	return ret_ok;
}


ret_t
cherokee_flcache_req_set_store (cherokee_flcache_t    *flcache,
				cherokee_connection_t *conn)
{
	ret_t                        ret;
	int                          dir;
	int                          file;
	cherokee_avl_flcache_node_t *entry = NULL;

	/* Add it to the tree
	 */
	ret = cherokee_avl_flcache_add (&flcache->request_map, conn, &entry);
	if ((ret != ret_ok) || (entry == NULL)) {
		return ret;
	}

	/* Set mode, ref count
	 */
	CHEROKEE_MUTEX_LOCK (&entry->ref_count_mutex);
	entry->ref_count += 1;
	CHEROKEE_MUTEX_UNLOCK (&entry->ref_count_mutex);

	entry->status = flcache_status_storing;

	/* Filename
	 */
	flcache->last_file_id += 1;

	dir  = (flcache->last_file_id / FILES_PER_DIR);
	file = (flcache->last_file_id % FILES_PER_DIR);

	cherokee_buffer_add_buffer (&entry->file, &flcache->local_directory);
	cherokee_buffer_add_str    (&entry->file, "/");
	cherokee_buffer_add_long10 (&entry->file, dir);
	cherokee_buffer_add_str    (&entry->file, "/");
	cherokee_buffer_add_long10 (&entry->file, file);

	/* Status
	 */
	conn->flcache.mode         = flcache_mode_in;
	conn->flcache.avl_node_ref = entry;

	return ret_ok;
}


static ret_t
inspect_header (cherokee_flcache_conn_t *flcache_conn,
		cherokee_buffer_t       *header,
		cherokee_connection_t   *conn)
{
	char                        *value;
	char                        *begin;
	char                        *end;
	const char                  *header_end;
	char                         chr_end;
	cherokee_avl_flcache_node_t *node        = flcache_conn->avl_node_ref;
	cherokee_boolean_t           via_found   = false;
	cherokee_buffer_t           *tmp         = THREAD_TMP_BUF2(CONN_THREAD(conn));

	begin      = header->buf;
	header_end = header->buf + header->len;

	while ((begin < header_end)) {
		end = cherokee_header_get_next_line (begin);
		if (end == NULL)
			break;

		chr_end = *end;
		*end    = '\0';

		/* Expire
		 */
		if (strncasecmp (begin, "Expires:", 8) == 0) {
			value = begin + 8;
			while ((*value == ' ') && (value < end)) value++;

			node->valid_until = 0;
			cherokee_dtm_str2time (value, end - value, &node->valid_until);
		}

		/* Content-length
		 */
		else if (strncasecmp (begin, "Content-Length:", 15) == 0) {
			*end = chr_end;

			while ((*end == CHR_CR) || (*end == CHR_LF))
				end++;

			cherokee_buffer_remove_chunk (header, begin - header->buf, end - begin);

			end = begin;
			continue;
		}

		/* Cache-Control
		 */
		else if (strncasecmp (begin, "Cache-Control:", 14) == 0) {
			value = begin + 8;
			while ((*value == ' ') && (value < end)) value++;

			if (strcasestr (begin, "private") ||
			    strcasestr (begin, "no-cache") ||
			    strcasestr (begin, "no-store") ||
			    strcasestr (begin, "must-revalidate") ||
			    strcasestr (begin, "proxy-revalidate"))
			{
				return ret_deny;
			}

			/* TODO: max-age= and s-maxage=
			 */
		}

		/* Set-cookie
		 */
		else if (strncasecmp (begin, "Set-cookie:", 11) == 0) {
			if (conn->flcache_cookies_disregard) {
				int                 re;
				void               *pcre;
				cherokee_list_t    *i;
				cherokee_boolean_t  matched = false;

				list_for_each (i, conn->flcache_cookies_disregard) {
					pcre = LIST_ITEM_INFO(i);

					re = pcre_exec (pcre, NULL, begin, end-begin, 0, 0, NULL, 0);
					if (re >= 0) {
						matched = true;
						break;
					}
				}
				if (! matched) {
					return ret_deny;

				}
			} else {
				return ret_deny;
			}
		}

		/* Via
		 */
		else if (strncasecmp (begin, "Via:", 4) == 0) {
			via_found = true;

			/* Build string */
			cherokee_buffer_clean (tmp);
			cherokee_buffer_add_str (tmp, ", ");
			cherokee_connection_build_host_port_string (conn, tmp);
			cherokee_buffer_add_str (tmp, " (Cherokee/"PACKAGE_VERSION")");

			/* Insert at the end */
			cherokee_buffer_insert_buffer (header, tmp, end - header->buf);
			end += tmp->len;
		}

	/* next: */
		*end = chr_end;

		while ((*end == CHR_CR) || (*end == CHR_LF))
			end++;
		begin = end;
	}

	if (! via_found) {
		cherokee_buffer_add_str (header, "Via: ");
		cherokee_connection_build_host_port_string (conn, header);
		cherokee_buffer_add_str (header, " (Cherokee/"PACKAGE_VERSION")" CRLF);
	}

	return ret_ok;
}


static ret_t
open_flconn_file (cherokee_flcache_t    *flcache,
		  cherokee_connection_t *conn)
{
	ret_t                        ret;
	cherokee_buffer_t            tmp   = CHEROKEE_BUF_INIT;
	cherokee_avl_flcache_node_t *entry = conn->flcache.avl_node_ref;

	conn->flcache.fd = cherokee_open (entry->file.buf, O_WRONLY | O_CREAT | O_NOFOLLOW, S_IRUSR|S_IWUSR);
	if (conn->flcache.fd == -1) {
		char *p;

		/* Try to create 'dir'
		 */
		p = strrchr (entry->file.buf, '/');
		if (p == NULL) {
			return ret_error;
		}

		cherokee_buffer_add (&tmp, entry->file.buf, p - entry->file.buf);

		ret = cherokee_mkdir_p_perm (&tmp, 0700, W_OK);
		if (ret != ret_ok) {
			LOG_CRITICAL (CHEROKEE_ERROR_FLCACHE_MKDIR, tmp.buf, "write");
			goto error;
		}

		TRACE (ENTRIES, "Created directory %s\n", flcache->local_directory.buf);

		/* Second chance
		 */
		conn->flcache.fd = cherokee_open (entry->file.buf, O_WRONLY | O_CREAT | O_NOFOLLOW, S_IRUSR|S_IWUSR);
		if (conn->flcache.fd == -1) {
			goto error;
		}
	}

	TRACE (ENTRIES, "Created flcache file %s\n", entry->file.buf);
	return ret_ok;

error:
	cherokee_buffer_mrproper (&tmp);
	return ret_error;
}

ret_t
cherokee_flcache_conn_commit_header (cherokee_flcache_conn_t *flcache_conn,
				     cherokee_connection_t   *conn)
{
	ret_t   ret;
	ssize_t written;

	/* Inspect header
	 */
	ret = inspect_header (flcache_conn, &flcache_conn->header, conn);
	if (ret == ret_deny) {
		cherokee_avl_flcache_node_t *entry = conn->flcache.avl_node_ref;

		cherokee_flcache_conn_clean (flcache_conn);
		cherokee_flcache_del_entry (CONN_VSRV(conn)->flcache, entry);

		return ret_ok;
	}

	/* Create the cache file
	 */
	ret = open_flconn_file (CONN_VSRV(conn)->flcache, conn);
	if (ret != ret_ok) {
		return ret_error;
	}

	TRACE (ENTRIES, "Writing header: %d bytes to fd=%d\n", flcache_conn->header.len, flcache_conn->fd);

	/* Write length
	 */
	do {
		written = write (flcache_conn->fd, &flcache_conn->header.len, sizeof(int));
	} while ((written == -1) && (errno == EINTR));

	if (unlikely (written != sizeof(int))) {
		return ret_error;
	}

	/* Write the header
	 */
	do {
		written = write (flcache_conn->fd, flcache_conn->header.buf, flcache_conn->header.len);
	} while ((written == -1) && (errno == EINTR));

	if (unlikely (written != flcache_conn->header.len)) {
		// TODO: check errno
		return ret_error;
	}

	return ret_ok;

}


ret_t
cherokee_flcache_conn_write_body (cherokee_flcache_conn_t *flcache_conn,
				  cherokee_connection_t   *conn)
{
	ssize_t written;

	TRACE (ENTRIES, "Writing body: %d bytes to fd=%d\n", conn->buffer.len, flcache_conn->fd);

	do {
		written = write (flcache_conn->fd, conn->buffer.buf, conn->buffer.len);
	} while ((written == -1) && (errno == EINTR));

	if (unlikely (written != conn->buffer.len)) {
		// TODO: check errno
		return ret_error;
	}

	flcache_conn->avl_node_ref->file_size += written;
	return ret_ok;
}


ret_t
cherokee_flcache_conn_send_header (cherokee_flcache_conn_t *flcache_conn,
				   cherokee_connection_t   *conn)
{
	ret_t   ret;
	ssize_t got;
	int     len;
	size_t  got2 = 0;

	/* Add cached headers
	 */
	do {
		got = read (flcache_conn->fd, &len, sizeof(int));
	} while ((got == -1) && (errno == EINTR));

	if (unlikely (got != sizeof(int))) {
		return ret_error;
	}

	TRACE (ENTRIES, "Reading header: len %d from fd=%d\n", len, flcache_conn->fd);

	ret = cherokee_buffer_read_from_fd (&conn->header_buffer, flcache_conn->fd, len, &got2);
	if (unlikely (ret != ret_ok)) {
		// TODO: check errno
		printf ("Error header %d\n", errno);
		return ret_error;
	}

	/* Add Content-Length
	 */
	cherokee_buffer_add_str      (&conn->header_buffer, "Content-Length: ");
	cherokee_buffer_add_ullong10 (&conn->header_buffer, flcache_conn->avl_node_ref->file_size);
	cherokee_buffer_add_str      (&conn->header_buffer, CRLF);

	/* X-Cache
	 */
	cherokee_buffer_add_str (&conn->header_buffer, "X-Cache: HIT from ");
	cherokee_connection_build_host_port_string (conn, &conn->header_buffer);
	cherokee_buffer_add_str (&conn->header_buffer, CRLF);

	/* Age (RFC2616, section 14.6)
	 */
	cherokee_buffer_add_str    (&conn->header_buffer, "Age: ");
	cherokee_buffer_add_long10 (&conn->header_buffer, cherokee_bogonow_now - flcache_conn->avl_node_ref->created_at);
	cherokee_buffer_add_str    (&conn->header_buffer, CRLF);

	return ret_ok;
}


ret_t
cherokee_flcache_conn_send_body (cherokee_flcache_conn_t *flcache_conn,
				 cherokee_connection_t   *conn)
{
	ret_t              ret;
	cherokee_boolean_t eof;
	size_t             got = 0;

	TRACE (ENTRIES, "Reading body from fd=%d\n", flcache_conn->fd);

	ret = cherokee_buffer_read_from_fd (&conn->buffer, flcache_conn->fd, DEFAULT_READ_SIZE, &got);

	if (got != 0) {
		flcache_conn->response_sent += got;
		eof = (flcache_conn->response_sent >= flcache_conn->avl_node_ref->file_size);
	}

	if (eof) {
		return (got)? ret_eof_have_data : ret_eof;
	}

	if (got) {
		return ret_ok;
	}

	if (ret != ret_ok) {
		return ret;
	}

	SHOULDNT_HAPPEN;
	return ret_error;
}


ret_t
cherokee_flcache_cleanup (cherokee_flcache_t *flcache)
{
	ret_t ret;

	TRACE (ENTRIES, "Cleaning up vserver cache '%s'\n", flcache->local_directory.buf);

	ret = cherokee_avl_flcache_cleanup (&flcache->request_map);
	if (unlikely (ret != ret_ok)) {
		return ret_error;
	}

	return ret_ok;
}


ret_t
cherokee_flcache_del_entry (cherokee_flcache_t          *flcache,
			    cherokee_avl_flcache_node_t *entry)
{
	ret_t ret;

	ret = cherokee_avl_flcache_del (&flcache->request_map, entry);
	TRACE (ENTRIES, "Removing expired Front-line cache entry '%s' - ret=%d\n", entry->file.buf, ret);

	return ret;
}


ret_t
cherokee_flcache_conn_clean (cherokee_flcache_conn_t *flcache_conn)
{
	cherokee_avl_flcache_node_t *entry = flcache_conn->avl_node_ref;

	/* Unreference entry
	 */
	if (entry != NULL) {

		/* The storage has finished */
		if (entry->status == flcache_status_storing) {
			entry->status = flcache_status_ready;
		}

		/* Reference countring */
		CHEROKEE_MUTEX_LOCK (&entry->ref_count_mutex);
		entry->ref_count -= 1;
		CHEROKEE_MUTEX_UNLOCK (&entry->ref_count_mutex);

		flcache_conn->avl_node_ref = NULL;
	}

	/* Front-line connection: clean up
	 */
	flcache_conn->header_sent   = 0;
	flcache_conn->response_sent = 0;
	flcache_conn->mode          = flcache_mdoe_undef;

	if (flcache_conn->fd != -1) {
		cherokee_fd_close (flcache_conn->fd);
		flcache_conn->fd = -1;
	}

	cherokee_buffer_mrproper (&flcache_conn->header);

	return ret_ok;
}
