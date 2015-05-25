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

var amcat = {};

/* Replace input-box with loading-image when clicked */
 $(function(){
	$("input[type=submit].nonajax").click(function(event){
		$(event.currentTarget).hide();
		$(event.currentTarget).parent().append('<img src="/media/img/misc/ajax-loading.gif" />');
	});
});


/* Enable multiselect */
$(function(){
   $.each($("select.multiselect"), function(i, el){
      $(el).multiselect({
         minWidth : 300,
         multiple : el.multiple,
         selectedList : 5
      }).multiselectfilter({filter: amcat.multiselectCheckIfMatches});
   });
});

function confirm_dialog(event) {
        event.preventDefault();
       
        var dialog = $('' +
            '<div class="modal fade" tabindex="-1">' +
                '<div class="modal-dialog"><div class="modal-content"><div class="modal-header">' +
                        '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                        '<h3 class="noline">Irreversible action</h3>' +
                '</div>' +
                '<div class="modal-body">' +
                '<p>' + $(event.currentTarget).attr("data-confirm")  + '</p>' +
                '</div>' +
                '<div class="modal-footer">' +
                    '<a href="#" class="btn cancel-button">Cancel</a>' +
                    '<a href="' +  $(event.currentTarget).attr("href") + '" class="btn btn-danger">Proceed</a>' +
                '</div>' +
            '</div></div></div>').modal("show");

        // Submit form if button has type=submit
        var btn = $(event.currentTarget);
        if(btn.is("[type=submit]")){
            dialog.find("a.btn-danger").click(function(event){
                event.preventDefault();
                btn.closest("form").submit();
            });
        }

        $(".cancel-button", dialog).click((function(){
            this.modal("hide");
        }).bind(dialog))
}


/* For <a> with a class 'confirm', display confirmation dialog */
$(function(){$("a.confirm").click(confirm_dialog);});


amcat.multiselectCheckIfMatches = function(event, matches){
    // used in the multiselects. Shows error message when no match is found in the filtering
    if( !matches.length ){
       $(event.target).multiselect('widget').find('.ui-multiselect-filter-msg').text('No matches found!');
    } else {
        $(event.target).multiselect('widget').find('.ui-multiselect-filter-msg').empty();
    }
}


amcat.check_fetch_results = function(state){
    /*
     * Check (label) results gathered so far. If all labels are
     * fetched, build table.
     *
     * (Ugly code below..)
     */
    var done = true;

    $.each(state.ajax_call_results.options, function(fieldname, data){
        if (done === false) return;

        if (data === null | state.ajax_call_results.labels[fieldname] === null){
            done = false;
        }
    });

    if (done === false) return;
    
    // All request finisched begin formatting!

    /* Inline function :-(, so we don't waste globals  */
    var re = /\{([^}]+)\}/g;
    var format = function(s, args) {
      /* Python(ish) string formatting:
      * >>> format('{0}', ['zzz'])
      * "zzz"
      * >>> format('{x}', {x: 1})
      * "1"
      */
      return s.replace(re, function(_, match){ return args[match]; });
    }

    /*
     * For every fieldname do:
     *   For every row do:
     *     format according to given label
     */
    $.each(state.ajax_call_results.labels, function(fieldname, labels){
        $.each(state.data.results, function(i, obj){
            if (labels[obj[fieldname]] !== undefined){
                obj[fieldname + "_id"] = obj[fieldname];

                obj[fieldname] = format(
                    state.ajax_call_results.options[fieldname].label,
                    labels[obj[fieldname]]
                );
            }
        });
    });

    state.callback(state.data);
}

amcat.single_fetch_finished = function(data, textStatus, jqXHR){
    /*
     * Called when new labels are fetched.
     */
    var fieldname = this[0];
    var state = this[1];

    var data_by_id = {};
    $.each(data, function(i, obj){
	if (obj != null)
            data_by_id[obj.id] = obj;
    });



    state.ajax_call_results.labels[fieldname] = data_by_id;
    amcat.check_fetch_results(state);
}

amcat.fetch_labels = function(data, textStatus, jqXHR, callback, url){
    /*
     * Modifies 'data' so includes labels. This used the HTTP OPTIONS
     * feature of django-rest-framework.
     *
     * @data, textStatus, jqXHR: normal jQuery AJAX callback arguments
     * @callback: function called when data is correctly 'labeled'
     * @url: url used to fetch data (and thus the url to fetch OPTIONS)
     */
    var state = {
        data : data,
        callback : callback,
        requests_finished : false,
        options : null,
        ajax_call_results : {
            options : {
                // fieldname : fetched_data || null
            },
            labels : {
                // fieldname : fetched_data || null
            }
        },
    };

    $.ajax({
        url : url,
        dataType : "json",
        type : "OPTIONS",
        success : (function(opts){
            state.options = opts;  

            $.each(opts.fields, (function(field, fieldtype){
                if (fieldtype !== "ModelChoiceField" | opts.models[field] === undefined){
                    return;
                }

                // Register AJAX call in state variable
                state.ajax_call_results.options[field] = null;
                state.ajax_call_results.labels[field] = null;

                var ids = [];
                $.each(state.data.results, function(i, obj){
                    // Ignore NULL values (field is optional)
                    if (obj[field] === null) return;

                    ids.push(obj[field]);
                });

                // Get labels
                $.ajax(opts.models[field], {
                    success : amcat.single_fetch_finished.bind([field, state]),
                    type : "GET",
                    data : {
                        id : ids,
                        format : "json",
                        paginate : false
                    },
                    traditional : true
                });

                // Get options
                $.ajax(opts.models[field], {
                    success : (function(data){
                        this[1].ajax_call_results.options[this[0]] = data;
                        amcat.check_fetch_results(this[1]);
                    }).bind([field, state]),
                    type : "OPTIONS"
                });

            }));

            // If no labels need to be fetched, also render table
            amcat.check_fetch_results(state);
        })
    });
}


/* Switch layouts */
$(function(){
    $("#layout-switcher").click(function(event){
        event.preventDefault();
        // Switch classes, etc.
        $(".container,.container-fluid").toggleClass("container container-fluid");
        $("#layout-switcher i").toggleClass("glyphicon-resize-small glyphicon-resize-full")
        $("body").focus();

        // Resize datatables
        $.each($.fn.dataTable.tables(), function(i, table){
            var settings = $(table).DataTable().settings()[0];
            settings.oApi._fnAdjustColumnSizing(settings);
        });

        // Make change permanent. TODO: Make it an API call.
        $.get("/navigator/?fluid=" + $("body > .container-fluid").length)
    });
});
