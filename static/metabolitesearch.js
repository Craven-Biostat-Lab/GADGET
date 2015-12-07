// script for gene search page
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
    var querystring = "q=" + q + "&genes=" + genesyms + "&geneop=" + geneop + "&species=" + species + "&usehomologs=" + usehomologs + "&orderby=" + key + "&usegenefile=" + usegenefile;
    window.location = "genesearch?" + querystring;
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
            
            hidespinner();     
            
            // show abstract count
            if (data.abstractcount) {
                $("span#abstractcount").html(data.abstractcount).show();
            }
            
            $(".show-with-results").fadeIn('slow');
            $("#results").fadeTo(200, 1);
            $("table#download").fadeIn('slow');
            
            $("#more").show();
            
            $('body,html').animate({scrollTop: $('div#description').offset().top - 10}, 600);   
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
        $.getJSON("genelist", queryString)
        .success(function(data)
        {
            if (data.validresult)
            {
                // append new genes to table
                $("#generank").append(data.result);
                hidespinner();
                $("#more").show();
            }
            else
            {
                // If "validresult" is false, we ran out of genes.  
                hidespinner();
                $("#more").hide(); 
                $("div#content").append("No more genes match your query!");
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
        var gene = $(this).attr("gene");
        var sym = $(this).attr("genesymbol");
        
        if ($("#generank div#abstracts" + gene).length == 0) // see if the tr for absracts exists
        {
            // the abstracts pane doesn't exist.
            hidepanes(gene); // hide other panes
            
            // how many abstracts for this gene?
            var abstractcount = $("div#gene" + gene).attr("hits");

            // genes query string argument
            var genearg = genesyms ? "(" + genesyms + ") AND " + sym : sym;

            // assemble querystring
            var querystring = "q=" + q + "&genes=" + genesyms + "&rowgene=" + sym + "&geneop=" + geneop + "&genesyms=" + genesyms + "&rowgene=" + sym + "&species=" + species + "&usehomologs=" + usehomologs + "&unique=" + gene + "&orderby=relevance" + "&abstractcount=" + abstractcount + "&usegenefile=" + usegenefile + "&genefileID=" + genefileID; 
            
            // set up abstract pane
            $("#generank div#gene" + gene).after('<div class="abstracts pane" id="abstracts' + gene + '"><img src="/static/spinner2.gif"></div>');
            
            // change link text
            $(this).text("Hide abstracts");

            // fetch and display abstracts
            $.get("abstractview.html", querystring)
            .success(function(result)
            {
                    // append abstracts to td
                    $("#generank div#abstracts" + gene + " img").remove(); // hide spinner
                    $("#generank div#abstracts" + gene).html(result); 
                    $("#generank div#abstracts" + gene).append('<a href="javascript:void(0);" class="hidepanes" gene="' + gene + '">&times; Hide abstracts</a>');
                    $("#generank div#abstracts" + gene).append('<a href="javascript:void(0);" class="hidepanes close-pane-x" gene="' + gene + '">&times;</a>');
                    
                    $("#generank div#abstracts" + gene).slideDown();
                    fetchabstracts(gene);
                
            })
            .error(function() 
            {
                flasherror();
            });
        }
        else // the abstract pane exists
        {
            // is the abstracts pane hidden?
            if (!$("#generank div#abstracts" + gene).is(":visible"))
            {
                // the abstract pane exists but is hidden
                // show the abstract pane
                hidepanes(gene);
                $("#generank div#abstracts" + gene).slideDown();

                $(this).text("Hide abstracts");
            }
            else
            {
                // the abstract exists and is visible
                // hide the abstract pane
                hidepanes(gene);
            }
        }
    });
    
        
    
    
    
    
    
    // show or hide external links (cross references) when the button gets clicked
    $("#generank").delegate("a.showcrossrefs", "click", function()
    {
        var gene = $(this).attr("gene");
        var sym = $(this).attr("genesymbol");
        
        if ($("#generank div#crossrefs" + gene).length == 0) // see if the tr for crossrefs exists
        {
            hidepanes(gene); // hide other panes
            
            // the tr for crossrefs doesn't exist, so make one
            $("#generank div#gene" + gene).after('<div class="crossrefs pane" style="display:none" id="crossrefs' + gene + '"><img src="/static/spinner2.gif"></div>');
        
            // assemble querystring
            var querystring = "gene=" + gene + "&genesymbol=" + sym;
            
            // fetch and display crossrefs
            $.getJSON("genecrossrefs", querystring)
            .success(function(data)
            {
                $("#generank div#crossrefs" + gene + " img").remove(); // hide spinner
                if (data.validresult)
                {
                    // display the cross references 
                    $("#generank div#crossrefs" + gene).html(data.result);
                    $("#generank div#crossrefs" + gene).append('<a href="javascript:void(0);" class="hidepanes" gene="' + gene + '">&times Hide external links</a>');
                    $("#generank div#crossrefs" + gene).append('<a href="javascript:void(0);" class="hidepanes close-pane-x" gene="' + gene + '">&times;</a>');
                    $("#generank div#crossrefs" + gene).slideDown();
                }
                else
                {
                    // collapse the pane, show an error message
                    $("#generank tr#crossrefs" + gene).remove();
                    hidepanes(gene);
                    flasherror();
                }
            })
            .error(function()
            {
                $("#generank div#crossrefs" + gene).remove();
                hidepanes(gene);
                flasherror();
            });
            
        }
        else // the tr for crossrefs exists
        {
            // is the crossrefs pane hidden?
            if (!$("#generank div#crossrefs" + gene).is(":visible"))
            {
                // the crossrefs pane exists but is hidden
                // show the crossrefs pane
                hidepanes(gene);
                $("#generank div#crossrefs" + gene).slideDown();
            }
            else
            {
                // the crossrefs pane is visible, so hide it
                hidepanes(gene);
            }
        }
    });


    // hide the pane when the "hide" link gets clicked
    $("#generank").delegate("a.hidepanes", "click", function()
    {
        var gene = $(this).attr("gene");
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


$(document).ready(function() {
    $('#search-button-metabolites').click(function() {
        $('#searchform').attr('action', '/gadget/metabolitesearch').submit();
    });
});
