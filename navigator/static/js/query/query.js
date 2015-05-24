"use strict";
/**************************************************************************
*          (C) Vrije Universiteit, Amsterdam (the Netherlands)            *
*                                                                         *
* This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     *
*                                                                         *
* AmCAT is free software: you can redistribute it and/or modify it under  *
* the terms of the GNU Affero General Public License as published by the  *
* Free Software Foundation, either version 3 of the License, or (at your  *
* option) any later version.                                              *
*                                                                         *
* AmCAT is distributed in the hope that it will be useful, but WITHOUT    *
* ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   *
* FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     *
* License for more details.                                               *
*                                                                         *
* You should have received a copy of the GNU Affero General Public        *
* License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  *
***************************************************************************/

define(["jquery", "query/renderers", "query/utils/dates"], function($, renderers, QueryDates){
    $.fn.queryscreen = function(options){
        return this.each(function(){
            _AmCATQueryScreen($, renderers, QueryDates, options);
        });
    }
});


function _AmCATQuery($, renderers, QueryDates, options){
    var renderContainer = $(this);
    var self = {};

    /**
     * Convenience function to load an existing saved query, and render its results.
     *
     * @param queryId
     */
    function load(queryId){

    }

    /**
     *
     * @param data
     */
    function render(data){

    }
}
