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

// stuff for gene file upload
// call on $(document).ready()
//function bindGeneUploadEvents()

$(document).ready( function ()
{
    // show upload form on "upload gene file" click
    $("div#header").delegate("a#uploadgenes", "click", function() 
    {
        $("div#geneuploadbox").html("<img src='static/spinner.gif' />");
        $("div#geneuploadbox").fadeIn();

        $.getJSON("/gadget/genefileupload")
        .success(function(data) 
        {
            $("div#geneuploadbox").html(data.page);
        })
        .error(flasherror);
    });


    $("div#geneuploadbox").delegate("form", "submit", function()
    {
        $.post($(this).attr("action"), $(this).serialize())
        .success( function(data)
        {
            if (data.success)
            {
                // gene UI changes here
                $("div#uploadbox").fadeOut();
            }
            else
            {
                $("div#uploadbox").html(data.page);
            }
        })
        .error(flasherror);

        return false; // stops the normal form submitting
    });
});
