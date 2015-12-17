var errormessage = "An error occurred!  Please check your internet connection, reload the page, and try again.  If the problem persists, please <a href='/contact.html'>contact us</a>.";

// display a message
function flash(message)
{
    $("div#errorbox span#errormessage").html(message);
    $("div#errorbox").slideDown();
}

// hide message
function hideflash()
{
    $("div#errorbox").slideUp();
}

// ajax spinner
function spin()
{
    $("#spinner").fadeIn("fast");
}

function hidespinner()
{
    $("#spinner").hide();
}


// show error message
function flasherror()
{
    flash(errormessage);
}



function initPopovers(selection) {
    // initialize help popovers
    selection.popover();
    
    // close popover on page click
    selection.click(function(e) {
        
        // if there's a popover already open, hide it
        selection.not(this).popover('hide');
 
        var icon = $(this);
        icon.popover('toggle');
        e.stopPropagation();
        e.preventDefault();
  
        // hide the popover on the next click
        $(document).one('click', function() {
            icon.popover('hide');
        });
  
    });
}


// bind events for gene file upload
$(document).ready( function ()
{
    // show upload form on "upload gene file" click
    $("div#search a#uploadgenes").click( function() 
    {
        showUploadForm();
    });

    // clear hidden form field when "clear" link is clicked
    $("div#search a#cleargenefile").click( function()
    {
        $("input#id_usegenefile").val("").trigger("change");
    });

    $("input#id_usegenefile").change(updategenebox);

    $("body").delegate("div#pagecover", "click", hideUploadForm);
    
    
    
    
    
    // submit search form on button click
    $('#search-button-genes').click(function() {
        $('#searchform').attr('action', '/gadget/genesearch').submit(); 
    });
       
    $('#search-button-metabolites').click(function() {
        $('#searchform').attr('action', '/gadget/metabolitesearch').submit();
    });
    
    
    

    
    
    
    
    initPopovers($('.help-icon'));
    
    
    
});


// called from the gene upload iframe if a file upload succeeds
function genefileUploadSuccess()
{
    $("input#id_usegenefile").val(true).trigger("change");
    window.setTimeout(hideUploadForm, 2000);
}


// grey out the gene input box if we're using a file
// called when the hidden "usegenefile" field is updated,
// and when the page is shown
function updategenebox()
{
    if ($("input#id_usegenefile").val())
    {
        // disable gene box if we're using a gene file
        $("input#id_genes").attr('disabled', 'disabled');
        $("input#id_genes").val("using file: " + getCookie("genefilename"));
        $("#cleargenefile-addon").show();
    }
    else
    {
        if ($("input#id_genes").attr("disabled"))
        {
            // if we're not using a gene file and the gene box is disabled, 
            // enable the gene box
            $("input#id_genes").val("").removeAttr("disabled");
            $("#cleargenefile-addon").hide();
        }
    }
}
$(window).bind('pageshow', updategenebox);


// from http://www.sitepoint.com/how-to-deal-with-cookies-in-javascript
function getCookie(name) 
{
    var regexp = new RegExp("(?:^" + name + "|;\\s*"+ name + ")=(.*?)(?:;|$)", "g");
    var result = regexp.exec(document.cookie);
    return (result === null) ? null : result[1];
}


function showUploadForm() 
{
    $("div#pagecover").css("opacity",0.6).fadeIn(); 
    $("div#geneuploadbox").html("<iframe src='/gadget/genefileupload' />");
    $("div#geneuploadbox").fadeIn();
}


function hideUploadForm()
{
    $("div#pagecover").fadeOut();
    $("div#geneuploadbox").fadeOut();
    return 0;
}





