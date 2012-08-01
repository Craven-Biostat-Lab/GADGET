// script for fetching and displaying abstracts
// uses jquery

// number of abstracts to fetch 
var abstractlimit = 15;

// clear and reset an "abstractcountainer" div
function resetabstracts(unique)
{
    var abstractdiv = $("div.abstractcontainer[abs_unique='" + unique + "']");

    abstractdiv.children("ul").empty();
    abstractdiv.attr("offset", 0);

    // hide "more abstracts" link
    $("a.moreabstracts[abs_unique='" + unique + "']").hide();
}

// fetch and display abstracts for the "abstractcontainer" div identified
// by the unique identifier
function fetchabstracts(unique)
{
    // find the abstractcontainer div with the unique identifier
    var abstractdiv = $("div.abstractcontainer[abs_unique='" + unique + "']");
    
    // spin
    $("img.spinner[abs_unique='" + unique + "']").show();
    
    // build query string
    var query = abstractdiv.attr("query") + "&orderby=" + abstractdiv.attr("orderby") + "&onlyreviews=" + abstractdiv.attr("onlyreviews") + "&limit=" + abstractlimit + "&offset=" + abstractdiv.attr("offset");
    
    $.getJSON(query)
    .success(function(data)
    {
        if (data.validresult)
        {
            // append abstracts to abstract div
            abstractdiv.children("ul").append(data.result);

            // update the offset
            var offset = parseInt(abstractdiv.attr("offset"));
            offset += abstractlimit;
            abstractdiv.attr("offset", offset);

            // show "more abstracts" link if there are more abstracts,
            // hide it otherwise
            $("a.moreabstracts[abs_unique='" + unique + "']").show();

            var abstractcount = parseInt(abstractdiv.attr("abstractcount"));
            if (isNaN(abstractcount))
            {
                // we don't know how many abstracts there are
                $("a.moreabstracts[abs_unique='" + unique + "']").show();
            }
            else
            {
                if (offset > abstractcount)
                {
                    // there are no more abstracts
                    $("a.moreabstracts[abs_unique='" + unique + "']").hide();
                }
                else
                {
                    // there are more abstracts
                    $("a.moreabstracts[abs_unique='" + unique + "']").show();
                }
            }
        }
        else
        {
            // hide "more abstracts" link if we don't have valid results
            $("a.moreabstracts[abs_unique='" + unique + "']").hide();
        }

        // hide spinner
        $("img.spinner[abs_unique='" + unique + "']").hide();
    })
    .error(function()
    {
        flasherror();

        // hide spinner and "more" link
        $("img.spinner[abs_unique='" + unique + "']").hide();
        $("a.moreabstracts[abs_unique='" + unique + "']").hide();
    });

}

// show more abstracts
$(document).delegate("a.moreabstracts", "click", function() {
    $(this).hide();
    fetchabstracts($(this).attr("abs_unique"));
});

// re-sort abstracts when the user clicks a link
$(document).delegate("a.sortabstracts", "click", function() {
    var unique = $(this).attr("abs_unique");
    
    // change link styles
    $("a.sortabstracts[abs_unique='" + unique + "']").removeClass("selected");
    $(this).addClass("selected");
    
    $("div.abstractcontainer[abs_unique='" + unique + "']").attr("orderby", $(this).attr("orderby"));
    resetabstracts(unique);
    fetchabstracts(unique);
});

$(document).delegate("input.onlyreviews", "change", function() {
    var unique = $(this).attr("abs_unique");

    
    $("div.abstractcontainer[abs_unique='" + unique + "']").attr("onlyreviews", $(this).is(":checked"));

    resetabstracts(unique);
    fetchabstracts(unique);
});
