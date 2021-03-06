// Script for metabolite search page
// Mostly copied from genesearch.js.
// requires jquery

// string variables "q", "genes", "geneop", "genesyms", "species", "usehomologs",
// 'usegenefile', and "orderby" declared on html page (from query string arguments)

// number of genes to fetch on page load
var initialLimit = 100;

// number of genes to fetch when the "more" button is pressed
var limit = 100;
var offset = 0;

// build the query string and redirect to a page with the new ordering
function order(key)
{
    // do nothing if we're already sorting by this key.
    if (orderby == key) { return; }

    var querystring = "q=" + q + "&genes=" + genesyms + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + key + "&usegenefile=" + usegenefile;
    window.location = "metabolitesearch?" + querystring;
}

// collapse the slider panes in the gene results table for a specific gene
function hidepanes(gene)
{
    $("#generank div#abstracts" + gene).slideUp('fast');
    $("#generank div#crossrefs" + gene).slideUp('fast');
    $("#generank a#showabs" + gene).text("Show abstracts");
}

$(document).ready(function()
{
    var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + initialLimit + "&usegenefile=" + usegenefile + "&genefileID=" + genefileID;
    offset += initialLimit;
    
    // get initial results
    spin();
    $.getJSON("metabolitelist", queryString)
    .success(function(data)
    {
        if (data.validresult)
        {
            // append new genes to table, show "more" button
            $("#generank").append(data.result);
            initPopovers($("#generank .more-synonyms"));
            
            hidespinner();     
            
            // show abstract count
            if (data.abstractcount) {
                $("span#abstractcount").html(data.abstractcount).show();
            }
            
            $(".show-with-results").fadeIn('slow');
            $("#results").fadeTo(200, 1);
            $("table#download").fadeIn('slow');
            
            $("#more").show();
            
            $('body,html').animate({scrollTop: $('div#description').offset().top - 10}, 700);   
        }
        else
        {
            // display error message
            flash(data.errmsg);
        }
    })
    .error(function() {hidespinner(); flasherror();} );
    
    // get and display more genes when the "more" button gets clicked
    $("#more").click(function()
    {
        var queryString = "q=" + q + "&genes=" + genes + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + orderby + "&limit=" + limit + "&offset=" + offset + "&usegenefile" + usegenefile + "&genefileID=" + genefileID;
        offset += limit;
        
        // hide "more" button while we're fetching more genes
        $("#more").hide();

        // get more genes
        spin();
        $.getJSON("metabolitelist", queryString)
        .success(function(data)
        {
            if (data.validresult)
            {
                // append new genes to table
                $("#generank").append(data.result);
                initPopovers($("#generank .more-synonyms"));
                hidespinner();
                $("#more").show();
            }
            else
            {
                // If "validresult" is false, we ran out of genes.  
                hidespinner();
                $("#more").hide(); 
                $("div#content").append("No more metabolites match your query!");
            }
        })
        .error(function() 
        {
            hidespinner();
            flasherror();
            $("#more").hide();    
        });
        
    });
    
    
    // show / hide abstracts when abstracts icon gets clicked
    $("#generank").delegate("a.showabstracts", "click", function()
    {
        var metabolite = $(this).attr("metabolite");
        
        if ($("#generank div#abstracts" + metabolite).length == 0) // see if the tr for absracts exists
        {
            // the abstracts pane doesn't exist.
            hidepanes(metabolite); // hide other panes
            
            // how many abstracts for this gene?
            var abstractcount = $("div#metabolite" + metabolite).attr("hits");

            // genes query string argument
            var genearg = genesyms; //genesyms ? "(" + genesyms + ") AND " + sym : sym;

            // assemble querystring
            var querystring = "q=" + q + "&genes=" + genesyms + "&geneop=" + geneop + "&genesyms=" + genesyms + "&species=" + species + "&usehomologs=" + usehomologs + "&unique=" + metabolite + "&orderby=relevance" + "&abstractcount=" + abstractcount + "&usegenefile=" + usegenefile + "&genefileID=" + genefileID + "&metabolite=" + metabolite; 
            
            // set up abstract pane
            $("#generank div#metabolite" + metabolite).after('<div class="abstracts pane" id="abstracts' + metabolite + '"><img src="/static/spinner2.gif"></div>');
            
            // change link text
            $(this).text("Hide abstracts");

            // fetch and display abstracts
            $.get("abstractview.html", querystring)
            .success(function(result)
            {
                    // append abstracts to td
                    $("#generank div#abstracts" + metabolite + " img").remove(); // hide spinner
                    $("#generank div#abstracts" + metabolite).html(result); 
                    $("#generank div#abstracts" + metabolite).append('<a href="javascript:void(0);" class="hidepanes" metabolite="' + metabolite + '">&times; Hide abstracts</a>');
                    $("#generank div#abstracts" + metabolite).append('<a href="javascript:void(0);" class="hidepanes close-pane-x" metabolite="' + metabolite + '">&times;</a>');
                    
                    $("#generank div#abstracts" + metabolite).slideDown();
                    fetchabstracts(metabolite);
                
            })
            .error(function() 
            {
                flasherror();
            });
        }
        else // the abstract pane exists
        {
            // is the abstracts pane hidden?
            if (!$("#generank div#abstracts" + metabolite).is(":visible"))
            {
                // the abstract pane exists but is hidden
                // show the abstract pane
                hidepanes(metabolite);
                $("#generank div#abstracts" + metabolite).slideDown();

                $(this).text("Hide abstracts");
            }
            else
            {
                // the abstract exists and is visible
                // hide the abstract pane
                hidepanes(metabolite);
            }
        }
    });
    
        
    
    
    
    
    
    

    // hide the pane when the "hide" link gets clicked
    $("#generank").delegate("a.hidepanes", "click", function()
    {
        var gene = $(this).attr("metabolite");
        hidepanes(gene);
    });
});


// preserve initial form values so the form matches the results on page load
// (without this, the form values get messed up when the user presses the back button.)

var initialquery = null;
var initialgenes = null;
var initialgeneop = null;
var initialspecies = null;
var initialhomologs = null;
var initialusegenefile = null;

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

    if (initialusegenefile == null) {initialusegenefile = $("input#id_usegenefile").val();}
    else 
    {
        $("input#id_usegenefile").val(initialusegenefile);
        updategenebox();
    }
});

