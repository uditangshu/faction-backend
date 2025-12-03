from fastapi import Request

async def dispatch(request: Request) -> bool:
        print(f"Request path: {request.url.path}")
        if "/admin" in request.url.path:
            print(request)   
            #check for the role of the user
            #then make decision to allow them to enter here
            return True

        else:
            # do something else for NON-admin routes
            print("Non-admin request")
            return True

