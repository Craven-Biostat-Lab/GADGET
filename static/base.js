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


