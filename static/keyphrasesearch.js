// script for keyphrase search page
// requires jquery

// string variables "q", "genes", "species", "usehomologs" and "orderby"
// declared on html page (from query string arguments)

// number of keywords to fetch on page load
var initialLimit = 100;

// number of keywords to fetch when the "more" button is pressed
var limit = 100;
var offset = 0;

// build the query string and redirect to a page with the new ordering
function order(key)
{
    var querystring = "q=" + q + "&genes=" + genesyms + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + key;
    window.location = "keywordsearch?" + querystring;
}

$(document).ready(function()
{
    var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + initialLimit;
    offset += initialLimit;
    
    // get initial results
    spin();
    $.getJSON("keywordlist", queryString)
    .success(function(data)
    {
        if (data.validresult)
        {
            $("table#keywords").append(data.result);
         
            // show abstract count
            if (data.abstractcount)
                $("span#abstractcount").html(data.abstractcount).show();
            
            $("div#description").show();
            $("#results").fadeTo(200, 1);
            $("table#download").fadeIn('slow');
            
            $("#more").show();
            hidespinner();     
        }
        else
        {
            // display error message
            flash(data.errmsg);
        }
    })
    .error(function() {hidespinner(); flasherror();} );
    
    
    // get and display more genes when the "more" button gets clicked
    $("input#more").click(function()
    {
        var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset;
        offset += limit;
        
        // hide "more" button while we're fetching more genes
        $("input#more").hide();

        // get more genes
        spin();
        $.getJSON("keywordlist", queryString)
        .success(function(data)
        {
            if (data.validresult)
            {
                // append new genes to table
                $("table#keywords").append(data.result);
                hidespinner();
                $("input#more").show();
            }
            else
            {
                // If "validresult" is false, we ran out of genes.  
                hidespinner();
                $("input#more").hide(); 
                $("div#content").append("No more genes match your query!");
            }
        })
        .error(function() 
        {
            hidespinner();
            flasherror();
            $("input#more").hide();    
        });
        
    });
});


// preserve initial form values so the form matches the results on page load
// (without this, the form values get messed up when the user presses the back button.)

var initialquery = null;
var initialgenes = null;
var initialgeneop = null;
var initialspecies = null;
var initialhomologs = null;

$(window).bind('pageshow', function() {
    if (initialquery == null) {initialquery = $("input#id_q").val();}
    else {$("input#id_q").val(initialquery);}
    
    if (initialgenes == null) {initialgenes = $("input#id_genes").val();}
    else {$("input#id_genes").val(initialgenes);}
    
    // if neither gene operator is selected, select 'any' by default
    // the django field 'inital' field doesn't work because the form is bound to the request.
    if($("input[name='geneop']:checked").length==0)
        {$("input[name='geneop'][value='any']").attr('checked', 'checked');}

    if (initialgeneop == null) {initialgeneop = $("input[name='geneop']:checked").attr('value');}
    else {$("input[name='geneop'][value='" + initialgeneop + "']").attr('checked', 'checked');}

    if (initialspecies == null) {initialspecies = $("select#id_species").val();}
    else {$("select#id_species").val(initialspecies);}
    
    if (initialhomologs == null) {initialhomologs = $("input#id_usehomologs").attr("checked");}
    else {$("input#id_usehomologs").attr("checked", initialhomologs);}
});
