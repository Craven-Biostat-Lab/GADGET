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
    $("div#spinner").fadeIn("fast");
}

function hidespinner()
{
    $("div#spinner").fadeOut("fast");
}


// show error message
function flasherror()
{
    flash(errormessage);
}


// bind events for gene file upload
$(document).ready( function ()
{
    // show upload form on "upload gene file" click
    $("div#header a#uploadgenes").click( function() 
    {
        showUploadForm();
    });

    // clear hidden form field when "clear" link is clicked
    $("div#header a#cleargenefile").click( function()
    {
        $("input#id_usegenefile").val("").trigger("change");
    });

    $("input#id_usegenefile").change(updategenebox);

    $("body").delegate("div#pagecover", "click", hideUploadForm);
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
    }
    else
    {
        if ($("input#id_genes").attr("disabled"))
        {
            // if we're not using a gene file and the gene box is disabled, 
            // enable the gene box
            $("input#id_genes").val("").removeAttr("disabled")
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
