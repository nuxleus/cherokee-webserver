/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*- */

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

#if !defined (CHEROKEE_INSIDE_CHEROKEE_H) && !defined (CHEROKEE_COMPILATION)
# error "Only <cherokee/cherokee.h> can be included directly, this file may disappear or change contents."
#endif

#ifndef CHEROKEE_UTIL_H
#define CHEROKEE_UTIL_H

#include <cherokee/common.h>
#include <cherokee/table.h>

#ifdef HAVE_NETINET_IN_H
# include <netinet/in.h>
#endif

#ifdef HAVE_ARPA_INET_H
# include <arpa/inet.h>
#endif 

#include <time.h>
#include <dirent.h>

#include <cherokee/buffer.h>


CHEROKEE_BEGIN_DECLS

#ifdef _WIN32
# define cherokee_stat(path,buf) cherokee_win32_stat(path,buf)
# define cherokee_error          GetLastError()
#else
# define cherokee_stat(path,buf) stat(path,buf)
# define cherokee_error          errno
#endif

/* Some global information
 */
const extern char *cherokee_months[]; 
const extern char *cherokee_weekdays[]; 

/* System
 */
ret_t cherokee_tls_init (void);

/* String management functions
 */
int   cherokee_hexit              (char c);
int   cherokee_isbigendian        (void);
char *cherokee_min_str            (char *s1, char *s2);
char *cherokee_strfsize           (unsigned long long size, char *buf);
int   cherokee_estimate_va_length (char *format, va_list ap);

/* Time management functions
 */

struct tm *cherokee_gmtime           (const time_t *timep, struct tm *result);
struct tm *cherokee_localtime        (const time_t *timep, struct tm *result);
long      *cherokee_get_timezone_ref (void);

/* Thread safe functions
 */
int        cherokee_readdir       (DIR *dirstream, struct dirent *entry, struct dirent **result);
ret_t      cherokee_gethostbyname (const char *hostname, void *addr);
ret_t      cherokee_syslog        (int priority, cherokee_buffer_t *buf);

/* Misc
 */
ret_t cherokee_fd_set_nonblocking (int fd);

ret_t cherokee_sys_fdlimit_get (cuint_t *limit);
ret_t cherokee_sys_fdlimit_set (cuint_t  limit);
void  cherokee_trace (const char *entry, const char *file, int line, const char *func, const char *fmt, ...);

/* Path walking
 */
ret_t cherokee_split_pathinfo     (cherokee_buffer_t  *path, 
				   int                 init_pos,
				   int                 allow_dirs,
				   char              **pathinfo,
				   int                *pathinfo_len);

ret_t cherokee_split_arguments    (cherokee_buffer_t *request,
				   int                init_pos,
				   char             **arguments,
				   int               *arguments_len);

ret_t cherokee_short_path         (cherokee_buffer_t *path);

ret_t cherokee_parse_query_string (cherokee_buffer_t *qstring, 
				   cherokee_table_t  *arguments);


CHEROKEE_END_DECLS

#endif /* CHEROKEE_UTIL_H */
